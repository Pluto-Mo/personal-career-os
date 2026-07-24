#!/usr/bin/env python3
"""Normalize an approved resume image for the resume header.

This script never downloads or invents an image. It only converts a local file
that the user has supplied or explicitly approved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageOps
except ImportError as exc:  # pragma: no cover - host runtime dependent
    raise SystemExit(
        "缺少 Pillow。请使用当前 Agent 自带的文档 Python 运行本脚本。"
    ) from exc

# Official print-ready TIFF assets can legitimately be very large. The script
# only accepts a user-supplied or explicitly approved local file, then reduces
# it before RGBA conversion to keep memory bounded.
Image.MAX_IMAGE_PIXELS = 300_000_000


PRESETS = {
    "portrait": {
        "pixels": (600, 810),
        "millimeters": (20, 27),
        "label": "证件照",
        "fixed_canvas": True,
    },
    "logo": {
        # Wide official lockups fill the width while square emblems are
        # limited by height, giving both a balanced visual weight.
        "pixels": (1200, 480),
        "millimeters": (40, 16),
        "label": "学校标识",
        "fixed_canvas": False,
    },
}


def crop_empty_margins(image: Image.Image) -> Image.Image:
    """Trim transparent or near-white margins without touching visible marks."""
    alpha = image.getchannel("A")
    alpha_minimum, _ = alpha.getextrema()
    if alpha_minimum < 255:
        mask = alpha.copy()
    else:
        rgb = image.convert("RGB")
        difference = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white"))
        mask = difference.convert("L").point(lambda value: 255 if value > 8 else 0)

    # Official print assets sometimes contain a one-pixel gray crop frame.
    # Ignore a narrow outer band while detecting content; the padding added
    # below restores genuinely edge-touching artwork without retaining frames.
    edge_band = max(2, round(min(image.width, image.height) * 0.01))
    mask.paste(0, (0, 0, image.width, edge_band))
    mask.paste(0, (0, image.height - edge_band, image.width, image.height))
    mask.paste(0, (0, 0, edge_band, image.height))
    mask.paste(0, (image.width - edge_band, 0, image.width, image.height))
    bounds = mask.getbbox()

    if not bounds:
        return image

    left, top, right, bottom = bounds
    padding = max(2, round(max(right - left, bottom - top) * 0.015))
    return image.crop(
        (
            max(0, left - padding),
            max(0, top - padding),
            min(image.width, right + padding),
            min(image.height, bottom + padding),
        )
    )


def normalize(source: Path, output: Path, kind: str) -> tuple[int, int]:
    preset = PRESETS[kind]
    target_width, target_height = preset["pixels"]
    with Image.open(source) as opened:
        reduction = max(
            1,
            min(
                max(1, opened.width // (target_width * 4)),
                max(1, opened.height // (target_height * 4)),
            ),
        )
        reduced = opened.reduce(reduction) if reduction > 1 else opened.copy()
        image = ImageOps.exif_transpose(reduced).convert("RGBA")
        if image.width <= 0 or image.height <= 0:
            raise ValueError("图片尺寸无效。")
        if not preset["fixed_canvas"]:
            if image.width > 8 and image.height > 8:
                image = image.crop((2, 2, image.width - 2, image.height - 2))
            image = crop_empty_margins(image)
        contained = ImageOps.contain(
            image,
            (target_width, target_height),
            method=Image.Resampling.LANCZOS,
        )
        if preset["fixed_canvas"]:
            canvas = Image.new("RGBA", (target_width, target_height), (255, 255, 255, 255))
            left = (target_width - contained.width) // 2
            top = (target_height - contained.height) // 2
            canvas.alpha_composite(contained, (left, top))
        else:
            canvas = Image.new("RGBA", contained.size, (255, 255, 255, 255))
            canvas.alpha_composite(contained)
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(output, format="PNG", dpi=(300, 300), optimize=True)
    return canvas.size


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把已确认的学校标识或证件照转换为简历页眉图片。")
    parser.add_argument("kind", choices=sorted(PRESETS), help="portrait=证件照；logo=学校标识（可含校徽+校名）")
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
    if preset["fixed_canvas"]:
        print(f"画布: {width} x {height} px；文档尺寸: {mm_width} x {mm_height} mm")
    else:
        print(f"图片: {width} x {height} px；文档最大边界: {mm_width} x {mm_height} mm（等比缩放）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
