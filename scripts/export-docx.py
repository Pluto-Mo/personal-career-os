#!/usr/bin/env python3
"""Export a Personal Career OS resume HTML file to an editable DOCX.

The HTML remains the layout source for PDF/PNG. This script reads the semantic
classes in that same finalized HTML and rebuilds them with native Word
paragraphs, tab stops, borders, and list numbering instead of asking
LibreOffice to convert CSS/flexbox into Word.

Usage:
    python export-docx.py resume.html
    python export-docx.py resume.html output.docx
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

try:
    from docx import Document
    from docx.enum.style import WD_STYLE_TYPE
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor
except ImportError as exc:  # pragma: no cover - depends on the host Agent runtime
    raise SystemExit(
        "缺少 python-docx。请让 Agent 使用其自带的文档运行时执行本脚本"
        "（Codex 可先加载 workspace dependencies），不要让最终用户手动配置。"
    ) from exc


IGNORED_TAGS = {"head", "script", "style", "svg"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Node | str"] = field(default_factory=list)

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())


class DOMParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag.lower(), {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if tag.lower() not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def walk(node: Node) -> Iterable[Node]:
    for child in node.children:
        if isinstance(child, Node):
            yield child
            if child.tag not in IGNORED_TAGS:
                yield from walk(child)


def find_class(node: Node, class_name: str) -> Node | None:
    return next((candidate for candidate in walk(node) if class_name in candidate.classes), None)


def find_tag(node: Node, tag: str) -> Node | None:
    return next((candidate for candidate in walk(node) if candidate.tag == tag), None)


def find_all(node: Node, *, tag: str | None = None, class_name: str | None = None) -> list[Node]:
    return [
        candidate
        for candidate in walk(node)
        if (tag is None or candidate.tag == tag)
        and (class_name is None or class_name in candidate.classes)
    ]


def text_of(node: Node | None) -> str:
    if node is None:
        return ""

    chunks: list[str] = []

    def collect(current: Node) -> None:
        if current.tag in IGNORED_TAGS:
            return
        for child in current.children:
            if isinstance(child, str):
                chunks.append(child)
            elif child.tag == "br":
                chunks.append("\n")
            else:
                collect(child)

    collect(node)
    return re.sub(r"[\t\r\f\v ]+", " ", "".join(chunks).replace("\xa0", " ")).strip()


def inline_segments(node: Node) -> list[tuple[str, bool]]:
    chars: list[tuple[str, bool]] = []

    def collect(current: Node, bold: bool = False) -> None:
        if current.tag in IGNORED_TAGS:
            return
        is_bold = bold or current.tag in {"b", "strong"}
        for child in current.children:
            if isinstance(child, str):
                chars.extend((character, is_bold) for character in child.replace("\xa0", " "))
            elif child.tag == "br":
                chars.append(("\n", is_bold))
            else:
                collect(child, is_bold)

    collect(node)

    normalized: list[tuple[str, bool]] = []
    pending_space = False
    for character, bold in chars:
        if character.isspace() and character != "\n":
            pending_space = bool(normalized)
            continue
        if pending_space and character != "\n":
            normalized.append((" ", bold))
        pending_space = False
        normalized.append((character, bold))

    while normalized and normalized[-1][0].isspace():
        normalized.pop()

    segments: list[tuple[str, bool]] = []
    for character, bold in normalized:
        if segments and segments[-1][1] == bold:
            segments[-1] = (segments[-1][0] + character, bold)
        else:
            segments.append((character, bold))
    return segments


def direct_children(node: Node, *, tag: str | None = None, class_name: str | None = None) -> list[Node]:
    return [
        child
        for child in node.children
        if isinstance(child, Node)
        and (tag is None or child.tag == tag)
        and (class_name is None or class_name in child.classes)
    ]


def set_style_fonts(style, latin: str = "Arial", east_asia: str = "Microsoft YaHei") -> None:
    style.font.name = latin
    r_pr = style.element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), latin)
    r_fonts.set(qn("w:hAnsi"), latin)
    r_fonts.set(qn("w:eastAsia"), east_asia)
    r_fonts.set(qn("w:cs"), latin)


def set_run_fonts(run, latin: str = "Arial", east_asia: str = "Microsoft YaHei") -> None:
    run.font.name = latin
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), latin)
    r_fonts.set(qn("w:hAnsi"), latin)
    r_fonts.set(qn("w:eastAsia"), east_asia)
    r_fonts.set(qn("w:cs"), latin)


def add_bottom_border(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    borders = p_pr.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        p_pr.append(borders)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "10")
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), "333333")
    borders.append(bottom)


def configure_styles(document) -> None:
    styles = document.styles

    normal = styles["Normal"]
    set_style_fonts(normal)
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.08

    def paragraph_style(name: str, *, size: float, bold: bool = False):
        style = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = normal
        set_style_fonts(style)
        style.font.size = Pt(size)
        style.font.bold = bold
        return style

    name_style = paragraph_style("Resume Name", size=20, bold=True)
    name_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_style.paragraph_format.space_after = Pt(1)
    name_style.paragraph_format.keep_with_next = True

    contact_style = paragraph_style("Resume Contact", size=9.5)
    contact_style.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
    contact_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    contact_style.paragraph_format.space_after = Pt(2)
    contact_style.paragraph_format.keep_with_next = True

    section_style = paragraph_style("Resume Section", size=12, bold=True)
    section_style.paragraph_format.space_before = Pt(11)
    section_style.paragraph_format.space_after = Pt(4)
    section_style.paragraph_format.keep_with_next = True

    entry_style = paragraph_style("Resume Entry Header", size=10.5)
    entry_style.paragraph_format.space_after = Pt(1.5)
    entry_style.paragraph_format.keep_with_next = True

    kv_style = paragraph_style("Resume Detail", size=10.2)
    kv_style.paragraph_format.space_after = Pt(1.5)
    kv_style.paragraph_format.line_spacing = 1.05

    bullet = styles["List Bullet"]
    set_style_fonts(bullet)
    bullet.font.size = Pt(10.2)
    bullet.paragraph_format.left_indent = Mm(4.2)
    bullet.paragraph_format.first_line_indent = Mm(-2.6)
    bullet.paragraph_format.space_before = Pt(0)
    bullet.paragraph_format.space_after = Pt(1.5)
    bullet.paragraph_format.line_spacing = 1.05


def add_segments(paragraph, segments: list[tuple[str, bool]]) -> None:
    for content, bold in segments:
        run = paragraph.add_run(content)
        run.bold = bold
        set_run_fonts(run)


def build_docx(html_path: Path, output_path: Path) -> tuple[int, int]:
    parser = DOMParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    page = find_class(parser.root, "page") or parser.root
    name_node = find_class(page, "name")
    name = text_of(name_node)
    sections = find_all(page, tag="section")

    if not name or not sections:
        raise ValueError("未识别到 .name 或 section；请使用 Personal Career OS 的 resume.html 结构。")

    document = Document()
    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(10.5)
    section.bottom_margin = Mm(10)
    section.left_margin = Mm(14)
    section.right_margin = Mm(14)
    section.header_distance = Mm(0)
    section.footer_distance = Mm(0)

    configure_styles(document)
    expected_fragments = [name]

    properties = document.core_properties
    properties.title = f"{name} - 简历"
    properties.subject = ""
    properties.author = ""
    properties.last_modified_by = ""
    properties.comments = ""
    properties.keywords = ""

    name_paragraph = document.add_paragraph(style="Resume Name")
    run = name_paragraph.add_run(name)
    run.bold = True
    set_run_fonts(run)

    contact = find_class(page, "contact")
    contact_items = [text_of(span) for span in find_all(contact, tag="span")] if contact else []
    contact_items = [item for item in contact_items if item]
    if contact_items:
        expected_fragments.extend(contact_items)
        contact_paragraph = document.add_paragraph(style="Resume Contact")
        contact_run = contact_paragraph.add_run(" ｜ ".join(contact_items))
        set_run_fonts(contact_run)

    bullet_count = 0
    for source_section in sections:
        heading = text_of(find_tag(source_section, "h2"))
        if not heading:
            continue
        expected_fragments.append(heading)
        heading_paragraph = document.add_paragraph(style="Resume Section")
        heading_run = heading_paragraph.add_run(heading)
        heading_run.bold = True
        set_run_fonts(heading_run)
        add_bottom_border(heading_paragraph)

        entries = direct_children(source_section, class_name="entry")
        for entry in entries:
            header = find_class(entry, "entry-head")
            if header:
                title = text_of(find_class(header, "entry-title"))
                role = text_of(find_class(header, "entry-role"))
                date = text_of(find_class(header, "entry-date"))
                expected_fragments.extend(item for item in (title, role, date) if item)
                header_paragraph = document.add_paragraph(style="Resume Entry Header")
                header_paragraph.paragraph_format.tab_stops.add_tab_stop(
                    Mm(182), WD_TAB_ALIGNMENT.RIGHT
                )
                if title:
                    title_run = header_paragraph.add_run(title)
                    title_run.bold = True
                    set_run_fonts(title_run)
                if role:
                    role_run = header_paragraph.add_run(f" ｜ {role}")
                    set_run_fonts(role_run)
                if date:
                    date_run = header_paragraph.add_run(f"\t{date}")
                    date_run.font.size = Pt(9.5)
                    date_run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
                    set_run_fonts(date_run)

            for detail in direct_children(entry, class_name="kv"):
                expected_fragments.append(text_of(detail))
                paragraph = document.add_paragraph(style="Resume Detail")
                add_segments(paragraph, inline_segments(detail))

            for item in find_all(entry, tag="li"):
                expected_fragments.append(text_of(item))
                paragraph = document.add_paragraph(style="List Bullet")
                item_run = paragraph.add_run(text_of(item))
                set_run_fonts(item_run)
                bullet_count += 1

        for detail in direct_children(source_section, class_name="kv"):
            expected_fragments.append(text_of(detail))
            paragraph = document.add_paragraph(style="Resume Detail")
            add_segments(paragraph, inline_segments(detail))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)

    with ZipFile(output_path) as archive:
        required = {"[Content_Types].xml", "word/document.xml", "word/styles.xml"}
        missing = required.difference(archive.namelist())
        if missing:
            raise ValueError(f"DOCX 包缺少必要文件: {', '.join(sorted(missing))}")
        document_xml = archive.read("word/document.xml")
        styles_xml = archive.read("word/styles.xml").decode("utf-8")

        root = ET.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = [
            "".join(text.text or "" for text in paragraph.findall(".//w:t", namespace))
            for paragraph in root.findall(".//w:p", namespace)
        ]
        all_text = re.sub(r"\s+", " ", "\n".join(paragraphs)).strip()
        missing_text = [
            fragment
            for fragment in expected_fragments
            if fragment and re.sub(r"\s+", " ", fragment).strip() not in all_text
        ]
        if missing_text:
            preview = "；".join(missing_text[:3])
            raise ValueError(f"DOCX 内容校验失败，缺少: {preview}")

        page_size = root.find(".//w:pgSz", namespace)
        if page_size is None:
            raise ValueError("DOCX 结构校验失败：没有页面尺寸。")
        width = int(page_size.get(qn("w:w"), "0"))
        height = int(page_size.get(qn("w:h"), "0"))
        if abs(width - 11906) > 2 or abs(height - 16838) > 2:
            raise ValueError(f"DOCX 结构校验失败：页面不是 A4（{width} x {height} twips）。")
        if bullet_count and ('w:styleId="ListBullet"' not in styles_xml or "<w:numPr>" not in styles_xml):
            raise ValueError("DOCX 结构校验失败：项目符号不是 Word 原生编号。")

    return len(sections), bullet_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 Personal Career OS 简历 HTML 导出为可编辑 DOCX。")
    parser.add_argument("html", type=Path, help="输入 resume.html")
    parser.add_argument("output", type=Path, nargs="?", help="输出 .docx；默认与 HTML 同名")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    html_path = args.html.expanduser().resolve()
    output_path = (args.output or html_path.with_suffix(".docx")).expanduser().resolve()

    if not html_path.is_file():
        print(f"错误: HTML 不存在: {html_path}", file=sys.stderr)
        return 2
    if output_path.suffix.lower() != ".docx":
        print("错误: 输出文件必须使用 .docx 扩展名。", file=sys.stderr)
        return 2

    try:
        section_count, bullet_count = build_docx(html_path, output_path)
    except (OSError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 3

    print(f"DOCX: {output_path}")
    print(f"结构: {section_count} 个区块，{bullet_count} 条项目符号")
    print("下一步: 用当前 Agent 的 DOCX 渲染能力生成逐页图片并检查版式。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
