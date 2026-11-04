#!/usr/bin/env python3
"""Generate a WeChat official-account main cover at 2.35:1.

Default output size is 2350x1000 PNG. The script supports an optional
background image and overlays Chinese title/subtitle locally for stable text.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageFilter

DEFAULT_WIDTH = 2350
DEFAULT_HEIGHT = 1000
ASPECT = DEFAULT_WIDTH / DEFAULT_HEIGHT
TITLE_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\Dengb.ttf",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
]
BODY_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\Deng.ttf",
    r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]


def load_font(size: int, candidates: list[str]) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in candidates:
        path = Path(font_path)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def cover_crop(image: Image.Image, width: int, height: int) -> Image.Image:
    image = image.convert("RGB")
    target_ratio = width / height
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        new_width = int(image.height * target_ratio)
        left = (image.width - new_width) // 2
        image = image.crop((left, 0, left + new_width, image.height))
    else:
        new_height = int(image.width / target_ratio)
        top = (image.height - new_height) // 2
        image = image.crop((0, top, image.width, top + new_height))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def make_gradient(width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), "#102033")
    px = image.load()
    for y in range(height):
        for x in range(width):
            t = (x / width) * 0.65 + (y / height) * 0.35
            r = int(14 + 26 * t)
            g = int(33 + 64 * t)
            b = int(55 + 75 * t)
            px[x, y] = (r, g, b)
    return image.filter(ImageFilter.GaussianBlur(radius=0.4))


def draw_grid(draw: ImageDraw.ImageDraw, width: int, height: int, step: int = 48) -> None:
    for x in range(0, width, step):
        alpha = 28 if x % (step * 4) else 46
        draw.line((x, 0, x, height), fill=(68, 118, 176, alpha), width=1)
    for y in range(0, height, step):
        alpha = 28 if y % (step * 4) else 46
        draw.line((0, y, width, y), fill=(68, 118, 176, alpha), width=1)


def draw_terminal_block(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int) -> None:
    draw.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=(14, 22, 34, 220), outline=(65, 120, 185, 100), width=2)
    for i in range(9):
        yy = y0 + 30 + i * 26
        line_w = int((x1 - x0) * (0.76 - i * 0.035))
        draw.rounded_rectangle((x0 + 28, yy, x0 + 28 + line_w, yy + 8), radius=4, fill=(83, 183, 255, 170))
        if i % 3 == 1:
            draw.rounded_rectangle((x0 + 28, yy + 12, x0 + 28 + int(line_w * 0.55), yy + 18), radius=3, fill=(255, 156, 89, 135))


def draw_geotech_panel(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int) -> None:
    draw.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=(17, 28, 45, 212), outline=(116, 158, 214, 100), width=2)
    layer_colors = [(91, 123, 171, 210), (110, 141, 184, 210), (142, 117, 86, 210), (96, 88, 78, 210)]
    top = y0 + 28
    height_total = y1 - y0 - 56
    layer_heights = [0.18, 0.22, 0.28, 0.32]
    current = top
    for ratio, color in zip(layer_heights, layer_colors):
        h = int(height_total * ratio)
        draw.rounded_rectangle((x0 + 26, current, x1 - 26, current + h), radius=12, fill=color)
        current += h + 10
    line_x = int(x0 + (x1 - x0) * 0.67)
    draw.line((line_x, y0 + 24, line_x, y1 - 24), fill=(255, 196, 87, 200), width=5)
    draw.line((line_x - 95, y0 + 62, line_x + 50, y0 + 152), fill=(241, 242, 246, 190), width=5)
    draw.line((line_x + 50, y0 + 152, line_x + 10, y1 - 70), fill=(241, 242, 246, 190), width=5)
    draw.ellipse((line_x - 8, y0 + 56, line_x + 8, y0 + 72), fill=(255, 196, 87, 220))


def make_blueprint_background(width: int, height: int) -> Image.Image:
    base = make_gradient(width, height).convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw_grid(draw, width, height, step=max(36, width // 52))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((int(width * 0.58), int(height * 0.08), int(width * 1.02), int(height * 0.94)), fill=(70, 115, 180, 56))
    gdraw.ellipse((int(width * 0.70), int(height * 0.00), int(width * 1.02), int(height * 0.46)), fill=(255, 146, 72, 34))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=42))
    base.alpha_composite(glow)

    draw.rounded_rectangle((int(width * 0.69), int(height * 0.14), int(width * 0.95), int(height * 0.46)), radius=30, fill=(20, 34, 54, 118))
    draw_terminal_block(draw, int(width * 0.72), int(height * 0.18), int(width * 0.94), int(height * 0.46))
    draw_geotech_panel(draw, int(width * 0.69), int(height * 0.54), int(width * 0.94), int(height * 0.82))

    draw.line((int(width * 0.54), int(height * 0.89), int(width * 0.98), int(height * 0.89)), fill=(36, 50, 72, 230), width=14)
    draw.line((int(width * 0.57), int(height * 0.93), int(width * 0.95), int(height * 0.93)), fill=(24, 34, 50, 245), width=22)

    for idx in range(6):
        x = int(width * (0.77 + idx * 0.03))
        draw.line((x, int(height * 0.76), x, int(height * 0.92)), fill=(78, 92, 112, 235), width=6)

    base.alpha_composite(overlay)
    return base.convert("RGB")


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for char in paragraph:
            trial = current + char
            if draw.textlength(trial, font=font) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines


def fit_font_and_lines(
    text: str,
    max_width: int,
    max_lines: int,
    start_size: int,
    min_size: int,
    candidates: list[str],
    draw: ImageDraw.ImageDraw,
) -> tuple[ImageFont.ImageFont, list[str]]:
    best_font = load_font(min_size, candidates)
    best_lines = wrap_text(text, best_font, max_width, draw)
    for size in range(start_size, min_size - 1, -4):
        font = load_font(size, candidates)
        lines = wrap_text(text, font, max_width, draw)
        if len(lines) <= max_lines:
            return font, lines
        best_font, best_lines = font, lines
    return best_font, best_lines[:max_lines]


def draw_text_block(
    image: Image.Image,
    badge: str,
    title: str,
    subtitle: str,
    tagline: str,
    width: int,
    height: int,
    use_panel: bool = True,
) -> None:
    draw = ImageDraw.Draw(image)
    margin_x = int(width * 0.08)
    max_text_width = int(width * 0.38)
    title_font, title_lines = fit_font_and_lines(
        title,
        max_text_width,
        3,
        int(height * 0.132),
        int(height * 0.090),
        TITLE_FONT_CANDIDATES,
        draw,
    )
    subtitle_font, subtitle_lines = fit_font_and_lines(
        subtitle,
        max_text_width,
        2,
        int(height * 0.050),
        int(height * 0.034),
        BODY_FONT_CANDIDATES,
        draw,
    )
    tagline_font = load_font(int(height * 0.031), BODY_FONT_CANDIDATES)
    badge_font = load_font(int(height * 0.040), TITLE_FONT_CANDIDATES)

    # Dark translucent panel for mobile readability. It reads as a deliberate
    # card on the generated blueprint background, but on a photo its straight
    # edges show through, so photographic covers rely on the scrim instead.
    if use_panel:
        panel = Image.new("RGBA", image.size, (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(panel)
        pdraw.rounded_rectangle(
            (margin_x - 48, int(height * 0.12), int(width * 0.60), int(height * 0.86)),
            radius=36,
            fill=(7, 12, 20, 132),
        )
        image.alpha_composite(panel)

    if badge:
        badge_y = int(height * 0.135)
        badge_w = int(draw.textlength(badge, font=badge_font) + 84)
        draw.rounded_rectangle((margin_x, badge_y, margin_x + badge_w, badge_y + 62), radius=18, fill="#E67129")
        draw.text((margin_x + 28, badge_y + 10), badge, font=badge_font, fill="#FFF8F1")

    y = int(height * 0.275)
    for line in title_lines:
        draw.text(
            (margin_x, y),
            line,
            font=title_font,
            fill="#F3F6FA",
            stroke_width=2,
            stroke_fill=(8, 14, 22),
        )
        bbox = draw.textbbox((margin_x, y), line, font=title_font)
        y += int((bbox[3] - bbox[1]) * 1.06)

    accent_y = y + int(height * 0.008)
    draw.rounded_rectangle((margin_x, accent_y, margin_x + 240, accent_y + 12), radius=6, fill="#FF8A33")

    if subtitle:
        y = accent_y + int(height * 0.055)
        for line in subtitle_lines:
            draw.text((margin_x, y), line, font=subtitle_font, fill="#D8E0EA")
            bbox = draw.textbbox((margin_x, y), line, font=subtitle_font)
            y += int((bbox[3] - bbox[1]) * 1.35)

    if tagline:
        tag_y = int(height * 0.885)
        draw.text((margin_x, tag_y), tagline, font=tagline_font, fill="#96A9BC")


def make_horizontal_scrim(
    width: int,
    height: int,
    left_alpha: int = 114,
    right_alpha: int = 58,
    fade_end: float = 0.68,
) -> Image.Image:
    """Left-to-right alpha ramp darkening the text side of the cover.

    Two stacked rectangles leave a hard seam at their shared edge. On the
    generated blueprint background that edge is hidden by the panel artwork,
    but on a photographic background it reads as an obvious vertical line.
    The ramp spends the same contrast budget without a visible boundary:
    left_alpha/right_alpha reproduce the previous 58 + 72 composite.
    """
    fade_end = min(1.0, max(0.05, fade_end))
    strip = Image.new("L", (width, 1))
    px = strip.load()
    for x in range(width):
        t = min(1.0, x / (width * fade_end))
        px[x, 0] = int(round(left_alpha + (right_alpha - left_alpha) * t))
    return strip.resize((width, height), Image.Resampling.BILINEAR)


def build_cover(args: argparse.Namespace) -> Image.Image:
    if args.width <= 0 or args.height <= 0:
        raise ValueError("width and height must be positive")
    ratio = args.width / args.height
    if abs(ratio - ASPECT) > 0.002:
        raise ValueError(f"cover ratio must be 2.35:1; got {ratio:.4f}")

    if args.background:
        base = cover_crop(Image.open(args.background), args.width, args.height)
    else:
        base = make_blueprint_background(args.width, args.height)

    image = base.convert("RGBA")
    # Photos vary in brightness, so the text side needs a heavier scrim there
    # than the blueprint background does.
    scrim_kwargs = (
        {"left_alpha": 150, "right_alpha": 88, "fade_end": 0.72} if args.background else {}
    )
    scrim = Image.new("RGBA", image.size, (0, 0, 0, 0))
    scrim.putalpha(make_horizontal_scrim(args.width, args.height, **scrim_kwargs))
    image.alpha_composite(scrim)
    draw_text_block(
        image,
        args.badge,
        args.title,
        args.subtitle,
        args.tagline,
        args.width,
        args.height,
        use_panel=args.background is None,
    )
    return image.convert("RGB")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a 2.35:1 WeChat article cover PNG.")
    parser.add_argument("--title", required=True, help="Main Chinese cover title")
    parser.add_argument("--badge", default="", help="Optional small category badge")
    parser.add_argument("--subtitle", default="", help="Optional subtitle")
    parser.add_argument("--tagline", default="工程案例 · 专业解读", help="Small bottom tagline")
    parser.add_argument("--output", required=True, help="Output PNG path")
    parser.add_argument("--background", help="Optional background image path")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = build_cover(args)
    image.save(output, format="PNG", optimize=True)
    print(f"saved={output}")
    print(f"size={image.width}x{image.height}")
    print(f"ratio={image.width / image.height:.2f}")


if __name__ == "__main__":
    main()
