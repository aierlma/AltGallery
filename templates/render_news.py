#!/usr/bin/env python3
"""Render an AltStore "NEW UPDATE" promo image from the shared SVG template.

Fills the placeholders in templates/news_update.template.svg with app values
and rasterizes to <out>/images/news.png at 1600x1200 (4:3). The intermediate
SVG is written to a temporary news.svg inside the app folder — so the icon's
relative href resolves — and removed afterwards; only the PNG is kept.

The image is deliberately minimal — icon, name, tagline, NEW UPDATE badge —
so it stays readable on a landscape phone and several fit per screen.
Other apps can reuse this verbatim — only the CLI args change.

Usage:
  render_news.py \
    --name PiliPlus \
    --tagline "BiliBili 第三方客户端" \
    --icon icon.png \
    --tint "#73b480" \
    --tint-alt "#00AEEF" \
    --out PiliPlus

Converters tried in order: rsvg-convert, qlmanage (macOS Quick Look).
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "news_update.template.svg"
WIDTH, HEIGHT = 1600, 1200


def render_png(svg_path: Path, png_path: Path) -> None:
    """Rasterize an SVG to a 1600x1200 PNG with the first tool available."""
    png_path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("rsvg-convert"):
        subprocess.run(
            ["rsvg-convert", "-o", str(png_path), str(svg_path)], check=True
        )
        return
    if shutil.which("qlmanage"):  # macOS fallback
        subprocess.run(
            ["qlmanage", "-t", "-s", str(WIDTH), "-o", str(png_path.parent), str(svg_path)],
            check=True,
            capture_output=True,
        )
        shutil.move(png_path.parent / f"{svg_path.stem}.svg.png", png_path)
        return
    sys.exit("error: no SVG rasterizer found (install librsvg or use macOS)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Render AltStore news promo image")
    ap.add_argument("--name", required=True, help="app display name")
    ap.add_argument("--tagline", required=True, help="short one-line descriptor")
    ap.add_argument("--icon", required=True, help="icon path, relative to --out dir")
    ap.add_argument("--tint", required=True, help="app brand color (config.toml [app] tint_color)")
    ap.add_argument("--tint-alt", required=True, help="secondary color (config.toml [source] tint_color)")
    ap.add_argument("--out", required=True, help="output directory (the app folder, e.g. PiliPlus)")
    args = ap.parse_args()

    tokens = {
        "{{APP_NAME}}": args.name,
        "{{TAGLINE}}": args.tagline,
        "{{ICON}}": args.icon,
        "{{TINT}}": args.tint,
        "{{TINT_ALT}}": args.tint_alt,
    }

    svg = TEMPLATE.read_text(encoding="utf-8")
    for token, value in tokens.items():
        svg = svg.replace(token, value)

    leftover = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", svg)))
    if leftover:
        sys.exit(f"error: unresolved template tokens: {leftover}")

    out = Path(args.out)
    png_path = out / "images" / "news.png"

    # Render from a temporary news.svg inside the app folder so the icon's
    # relative href resolves; remove it afterwards — only the PNG is kept.
    svg_path = out / "news.svg"
    try:
        svg_path.write_text(svg, encoding="utf-8")
        render_png(svg_path, png_path)
    finally:
        svg_path.unlink(missing_ok=True)

    size = png_path.stat().st_size
    print(f"wrote {png_path} ({size/1024:.0f} KiB)")


if __name__ == "__main__":
    main()
