#!/usr/bin/env python3
"""Normalize an approved resume image into the fixed header canvas.

This script never downloads or invents an image. It only converts a local file
that the user has supplied or explicitly approved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover - host runtime dependent
    raise SystemExit(
        "缺少 Pillow。请使用当前 Agent 自带的文档 Python 运行本脚本。"
    ) from exc


PRESETS = {
    "portrait": {
        "pixels": (600, 810),
        "millimeters": (20, 27),
        "label": "证件照",
    },
    "logo": {
        "pixels": (960, 540),
        "millimeters": (32, 18),
        "label": "学校校徽",
    },
}


def normalize(source: Path, output: Path, kind: str) -> tuple[int, int]:
    preset = PRESETS[kind]
    target_width, target_height = preset["pixels"]
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
        if image.width <= 0 or image.height <= 0:
            raise ValueError("图片尺寸无效。")
        contained = ImageOps.contain(
            image,
            (target_width, target_height),
            method=Image.Resampling.LANCZOS,
        )
        canvas = Image.new("RGBA", (target_width, target_height), (255, 255, 255, 255))
        left = (target_width - contained.width) // 2
        top = (target_height - contained.height) // 2
        canvas.alpha_composite(contained, (left, top))
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(output, format="PNG", dpi=(300, 300), optimize=True)
    return target_width, target_height


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把已确认的校徽或证件照转换为固定简历图片框。")
    parser.add_argument("kind", choices=sorted(PRESETS), help="portrait=证件照；logo=学校校徽")
    parser.add_argument("input", type=Path, help="用户提供或确认使用的本地图片")
    parser.add_argument("output", type=Path, help="输出 PNG")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_file():
        print(f"错误: 输入图片不存在: {source}", file=sys.stderr)
        return 2
    if source == output:
        print("错误: 标准化图片必须另存，不能覆盖用户提供的原图。", file=sys.stderr)
        return 2
    if output.suffix.lower() != ".png":
        print("错误: 标准化图片必须输出为 .png。", file=sys.stderr)
        return 2
    try:
        width, height = normalize(source, output, args.kind)
    except (OSError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 3
    preset = PRESETS[args.kind]
    mm_width, mm_height = preset["millimeters"]
    print(f"{preset['label']}: {output}")
    print(f"画布: {width} x {height} px；文档尺寸: {mm_width} x {mm_height} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
