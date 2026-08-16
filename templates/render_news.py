#!/usr/bin/env python3
"""Render an AltStore "NEW UPDATE" promo image from the shared SVG template.

Fills the placeholders in templates/news_update.template.svg with app values
and rasterizes to <out>/images/news.png at 1600x1200 (4:3). The intermediate
SVG is written to a temporary news.svg inside the app folder — so the icon's
relative href resolves — and removed afterwards; only the PNG is kept.

Configuration comes from <out>/news.toml (see the template below); any CLI
flag overrides its news.toml counterpart. Colors left unset are derived into
a harmonious scheme:
  - tint / tint_alt   -> [app] / [source] tint_color
  - background        -> light shade of the icon's dominant color, so the
                         promo blends with the app's artwork; falls back to
                         a dark tint-derived base when the icon is unreadable
  - text_color        -> white (or black for light backgrounds)
  - tagline_color     -> derived from the background hue

The name's cap top lines up with the icon's top edge, and the description
wraps onto several lines (explicit newlines are honored) and is sized as
large as it can be without overflowing the right column or dropping below
the NEW UPDATE badge — so both columns share a vertical span and the promo
stays readable on a landscape phone and several fit per screen.

Usage:
  render_news.py --out PiliPlus              # everything from PiliPlus/news.toml
  render_news.py --out Apollo-Reborn \
    --tagline "New tagline"                  # CLI overrides news.toml

news.toml:
  name = "PiliPlus"
  tagline = "BiliBili 第三方客户端"            # "\n" in the value wraps too
  # Optional — unset colors are derived from config.toml:
  # [colors]
  # tint = "#73b480"             badge/glow accent (default: [app] tint_color)
  # tint_alt = "#00AEEF"         secondary accent (default: [source] tint_color)
  # background = "#0C111D"       dark gradient base (default: derived from tint)
  # text_color = "#FFFFFF"       app name color (default: auto white/black)
  # tagline_color = "#AABDD6"    subtitle color (default: derived from background)

Converters tried in order: rsvg-convert, qlmanage (macOS Quick Look).
"""

import argparse
import colorsys
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib

TEMPLATE = Path(__file__).resolve().parent / "news_update.template.svg"
WIDTH, HEIGHT = 1600, 1200

# Right column geometry from the template: text starts at x=640 and must
# stay inside the 1600-wide canvas with ~100px of right margin.
TEXT_X = 640
RIGHT_MARGIN = 100
MAX_TEXT_WIDTH = WIDTH - RIGHT_MARGIN - TEXT_X  # 860

# Left column geometry, shared with the template. The name's cap top aligns
# with the icon's top edge (y=343), and the description's bottom must stay
# above the badge's bottom edge (857) — the description font is shrunk to
# enforce this.
ICON_X, ICON_Y, ICON_SIZE = 150, 343, 350
BADGE_X, BADGE_Y, BADGE_W, BADGE_H = 125, 773, 400, 84
BADGE_BOTTOM = BADGE_Y + BADGE_H  # 857
GAP_DESC = 40  # gap between the app name and the description

# Approximate rendered width per ASCII char as an em fraction, used for the
# description's line-wrapping and as a fallback when the real renderer can't
# be probed. Calibrated from rsvg-convert renders of the template's font
# stack; CJK glyphs are full-width (~1em). Overestimating slightly is safe —
# it only wraps/shapes a bit more conservatively than strictly needed.
NAME_WIDTH_FACTOR = 0.55     # app name, weight 800
TAGLINE_WIDTH_FACTOR = 0.50  # description, weight 600

# Font-size caps. The name and description are fitted as large as they can
# be without overflowing the right column or the vertical space above the
# badge, so text stays readable when AltStore shows the image small.
NAME_MAX = 180
TAGLINE_MAX = 72
TAGLINE_MIN = 30  # floor for a pathologically long description
NAME_LETTER_SPACING = 1  # template name uses letter-spacing="1"
CAP_HEIGHT_FACTOR = 0.73  # fallback cap-top height (em) when unmeasurable

FONT_STACK = (
    "'Helvetica Neue','Hiragino Sans GB','PingFang SC','Noto Sans CJK SC',"
    "'Microsoft YaHei',sans-serif"
)

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def text_width(text: str, font_size: int, factor: float) -> float:
    """Estimated rendered width of ``text`` at ``font_size``."""
    width = 0.0
    for ch in text:
        width += 1.0 if ord(ch) >= 0x2E80 else factor  # CJK is full-width
    return width * font_size


def fit_font_size(text: str, font_size: int, factor: float) -> int:
    """``font_size`` as-is if ``text`` fits the column, otherwise shrunk
    so it does."""
    if not text:
        return font_size
    width = text_width(text, font_size, factor)
    if width <= MAX_TEXT_WIDTH:
        return font_size
    return max(1, int(font_size * MAX_TEXT_WIDTH / width))


def _longest_prefix(text: str, font: int, factor: float, max_width: int) -> int:
    """Length of the longest prefix of ``text`` that fits ``max_width``."""
    lo, hi = 1, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if text_width(text[:mid], font, factor) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return max(lo, 1)


def wrap_text(text: str, font: int, factor: float, max_width: int) -> list[str]:
    """Split ``text`` into lines that fit ``max_width`` at ``font``.

    Explicit ``\\n`` always breaks a line; lines are additionally wrapped at
    whitespace, with long CJK runs / single words character-wrapped as a
    fallback. Keeps the description large and readable on several lines
    instead of shrinking it onto one.
    """
    lines: list[str] = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            lines.append("")
            continue
        current = ""
        for word in para.split(" "):
            trial = f"{current} {word}" if current else word
            if text_width(trial, font, factor) <= max_width:
                current = trial
                continue
            if current:
                lines.append(current)
            current = word
            # A single token can still be wider than the column: break it up.
            while current and text_width(current, font, factor) > max_width:
                k = _longest_prefix(current, font, factor, max_width)
                lines.append(current[:k])
                current = current[k:]
        if current:
            lines.append(current)
    return lines


def _probe(text: str, weight: int) -> tuple[float, float] | None:
    """Rasterize ``text`` at font-size 100 with the template's font stack and
    return ``(width_em, ascent_em)`` where ``ascent_em`` is the cap-top height
    above the baseline (probe baseline is y=260).

    Returns None when measurement isn't available (no rsvg-convert or no
    Pillow); callers then fall back to the per-char estimate / constants.
    These are the *actual* renderer metrics, so the name can be fitted right
    up to the column edge and aligned to the icon without guessing.
    """
    if not shutil.which("rsvg-convert"):
        return None
    try:
        from PIL import Image
    except ImportError:
        return None

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="4000" height="300"'
        ' viewBox="0 0 4000 300">'
        '<rect width="4000" height="300" fill="#000"/>'
        f'<text x="0" y="260" font-family="{FONT_STACK}" font-size="100"'
        f' font-weight="{weight}" fill="#fff">{escape(text)}</text></svg>'
    )
    with tempfile.TemporaryDirectory() as td:
        svg_path = Path(td) / "probe.svg"
        png_path = Path(td) / "probe.png"
        svg_path.write_text(svg, encoding="utf-8")
        try:
            subprocess.run(
                ["rsvg-convert", "-o", str(png_path), str(svg_path)],
                check=True,
                capture_output=True,
            )
            img = Image.open(png_path).convert("RGB")
            w, h = img.size
            px = img.load()
            minx, maxx, miny, maxy = w, -1, h, -1
            for y in range(h):
                for x in range(w):
                    r, g, b = px[x, y]
                    if r > 128 and g > 128 and b > 128:
                        if x < minx:
                            minx = x
                        if x > maxx:
                            maxx = x
                        if y < miny:
                            miny = y
                        if y > maxy:
                            maxy = y
            if maxx < 0:
                return None
            return (maxx - minx + 1) / 100.0, (260 - miny) / 100.0
        except (subprocess.CalledProcessError, OSError, ValueError):
            return None


def measure_glyph_em(text: str, weight: int) -> float | None:
    """Rendered glyph width of ``text`` in ems (per 100px font)."""
    metrics = _probe(text, weight)
    return metrics[0] if metrics else None


def measure_font_ascent_em(weight: int) -> float | None:
    """Cap-top height of the template font at ``weight`` in ems, measured from
    a capital 'A' — used to line the app name's top edge up with the icon."""
    metrics = _probe("A", weight)
    return metrics[1] if metrics else None


def fit_name_font(name: str) -> int:
    """Largest app-name font size that fits the right column (cap ``NAME_MAX``),
    using the measured renderer width where available, else the estimate."""
    if not name:
        return NAME_MAX
    glyph_em = measure_glyph_em(name, 800)
    if glyph_em is not None:
        gaps = max(len(name) - 1, 0) * NAME_LETTER_SPACING
        if glyph_em * NAME_MAX + gaps <= MAX_TEXT_WIDTH:
            return NAME_MAX
        return max(1, int((MAX_TEXT_WIDTH - gaps) / glyph_em))
    return fit_font_size(name, NAME_MAX, NAME_WIDTH_FACTOR)


def fit_tagline(tagline: str, max_height: float) -> tuple[list[str], int]:
    """The description wrapped onto lines and sized to fit ``max_height`` px.

    A short description stays on one line at full size when the measured
    renderer width proves it fits; otherwise it's word-wrapped (explicit
    ``\\n`` always breaks). Wrapping — not shrinking — keeps the text large,
    but the whole block is also constrained to ``max_height`` so its bottom
    stays above the NEW UPDATE badge. The per-char estimate can under-measure
    wide glyphs, so each wrapped line is verified against the real renderer
    and the font shrunk if a line overflows.
    """
    if not tagline.strip():
        return [], TAGLINE_MAX
    # Fast path: exact single-line fit when the real renderer says it fits.
    if "\n" not in tagline:
        glyph_em = measure_glyph_em(tagline, 600)
        if glyph_em is not None and glyph_em * TAGLINE_MAX <= MAX_TEXT_WIDTH:
            font = max(TAGLINE_MIN, min(TAGLINE_MAX, int(max_height / 1.5)))
            return [tagline.strip()], font
    font = TAGLINE_MAX
    lines = wrap_text(tagline, font, TAGLINE_WIDTH_FACTOR, MAX_TEXT_WIDTH)
    for _ in range(8):
        # 1) Horizontal: any line the real renderer would clip shrinks the font.
        ems = [measure_glyph_em(l, 600) for l in lines if l]
        if ems and all(e is not None for e in ems) and max(ems) * font > MAX_TEXT_WIDTH:
            font = max(TAGLINE_MIN, int(MAX_TEXT_WIDTH / max(ems)))
            lines = wrap_text(tagline, font, TAGLINE_WIDTH_FACTOR, MAX_TEXT_WIDTH)
            continue
        # 2) Vertical: whole description must fit above the badge.
        if len(lines) * 1.5 * font <= max_height or font <= TAGLINE_MIN:
            break
        font = max(TAGLINE_MIN, int(max_height / (len(lines) * 1.5)))
        lines = wrap_text(tagline, font, TAGLINE_WIDTH_FACTOR, MAX_TEXT_WIDTH)
    return lines, font


def build_tagline_lines(
    lines: list[str], y_positions: list[float], font: int, color: str
) -> str:
    """One ``<text>`` element per wrapped description line, left-aligned at
    the right column's x origin with its own baseline."""
    parts = []
    for y, line in zip(y_positions, lines):
        parts.append(
            f'  <text x="{TEXT_X}" y="{y:.0f}" font-family="{FONT_STACK}"'
            f' font-size="{font}" font-weight="600" fill="{color}"'
            f' text-anchor="start">{escape(line)}</text>'
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Color helpers (all hex "#RRGGBB" in and out)
# ---------------------------------------------------------------------------

def _hex_to_hls(value: str) -> tuple[float, float, float]:
    hx = value.lstrip("#")
    r, g, b = (int(hx[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)


def _hls_to_hex(h: float, l: float, s: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02X}{:02X}{:02X}".format(
        round(r * 255), round(g * 255), round(b * 255)
    )


def check_hex(value: str, what: str) -> str:
    """Validate a #RRGGBB color from news.toml; return it normalized."""
    if not _HEX_RE.match(value):
        sys.exit(f"error: {what} must be #RRGGBB, got {value!r}")
    return value.upper()


def derive_background(tint: str) -> str:
    """Dark gradient base in the tint's hue: keep hue, tone saturation way
    down, pin lightness low — reads as a deep tint-tinted navy."""
    h, _l, s = _hex_to_hls(tint)
    return _hls_to_hex(h, 0.09, min(s * 0.6, 0.5))


def derive_light_background(color: str) -> str:
    """Soft light background from an icon color: keep the hue, push
    lightness high and saturation low — a pale tint the icon blends with."""
    h, _l, s = _hex_to_hls(color)
    return _hls_to_hex(h, 0.88, min(s, 0.35))


def derive_bg_stops(bg: str) -> tuple[str, str]:
    """Lighter mid-stop and darker end-stop of the background gradient.
    The ramp adapts to the base lightness: light backgrounds get a subtle
    ramp, dark ones the original stronger one."""
    h, l, s = _hex_to_hls(bg)
    if l > 0.55:
        return _hls_to_hex(h, min(l + 0.05, 0.97), s), _hls_to_hex(h, max(l - 0.08, 0.55), s)
    return _hls_to_hex(h, min(l + 0.08, 0.55), s), _hls_to_hex(h, max(l - 0.03, 0.03), s)


def auto_text_color(bg: str) -> str:
    """White on dark backgrounds, black on light ones."""
    _h, l, _s = _hex_to_hls(bg)
    return "#111111" if l > 0.55 else "#FFFFFF"


def derive_tagline_color(bg: str) -> str:
    """Tagline shade derived from the background: a light tint on dark
    backgrounds, a darker readable shade on light ones."""
    h, l, s = _hex_to_hls(bg)
    if l > 0.55:
        return _hls_to_hex(h, max(l - 0.35, 0.35), min(s + 0.15, 0.45))
    return _hls_to_hex(h, 0.72, min(s, 0.35))


def extract_icon_color(icon_path: Path) -> str | None:
    """Dominant colorful color of the app icon, for a light background.

    Rasterizes the icon to a 64x64 BMP via sips, buckets the pixels, and
    scores buckets by pixel count x (saturation - 0.15) so a light design's
    background color doesn't win over its colorful elements. Returns None
    when the icon can't be read or holds no usable color.
    """
    tmp = icon_path.with_suffix(".bmp")
    try:
        subprocess.run(
            ["sips", "-s", "format", "bmp", "-z", "64", "64", str(icon_path), "--out", str(tmp)],
            check=True,
            capture_output=True,
        )
        data = tmp.read_bytes()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    finally:
        tmp.unlink(missing_ok=True)

    try:
        off = struct.unpack_from("<I", data, 10)[0]
        w = abs(struct.unpack_from("<i", data, 18)[0])
        h = abs(struct.unpack_from("<i", data, 22)[0])
        bpp = struct.unpack_from("<H", data, 28)[0]
        flip = struct.unpack_from("<i", data, 22)[0] > 0
        row_bytes = w * (bpp // 8)
    except struct.error:
        return None

    buckets: Counter = Counter()
    for y in range(h):
        src_y = (h - 1 - y) if flip else y
        row = data[off + src_y * row_bytes : off + src_y * row_bytes + row_bytes]
        if len(row) < row_bytes:
            return None
        for x in range(w):
            # BGRA in 32bpp (sips output); 24bpp rows are BGR, alpha assumed 255
            b, g, r = row[x * (bpp // 8)], row[x * (bpp // 8) + 1], row[x * (bpp // 8) + 2]
            a = row[x * (bpp // 8) + 3] if bpp == 32 else 255
            if a < 128:
                continue
            if (r > 235 and g > 235 and b > 235) or (r < 20 and g < 20 and b < 20):
                continue  # near-white / near-black (borders, glare, alpha void)
            buckets[(r // 16 * 16, g // 16 * 16, b // 16 * 16)] += 1

    if not buckets:
        return None
    total = sum(buckets.values())
    best, best_score = None, 0.0
    for (r, g, b), n in buckets.items():
        score = n * max(saturation(r, g, b) - 0.15, 0.0) / total
        if score > best_score:
            best, best_score = (r, g, b), score
    if best is None:
        return None
    return "#{:02X}{:02X}{:02X}".format(*best)


def saturation(r: int, g: int, b: int) -> float:
    """HSL saturation (0..1) of an RGB tuple."""
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 510
    if l == 0 or l == 1:
        return 0.0
    return (mx - mn) / (2 - mx / 255 - mn / 255) if l > 0.5 else (mx - mn) / (mx + mn)


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


def load_configs(out: Path) -> tuple[dict, dict]:
    """``news.toml`` and the app's ``config.toml`` as raw dicts ({} if absent
    or unreadable)."""
    news: dict = {}
    path = out / "news.toml"
    if path.exists():
        try:
            with open(path, "rb") as f:
                news = tomllib.load(f)
        except tomllib.TOMLDecodeError as exc:
            sys.exit(f"error: {path}: invalid TOML: {exc}")
    cfg: dict = {}
    path = out / "config.toml"
    if path.exists():
        try:
            with open(path, "rb") as f:
                cfg = tomllib.load(f)
        except tomllib.TOMLDecodeError:
            pass  # not ours to parse — just skip the tint defaults
    return news, cfg


def main() -> None:
    ap = argparse.ArgumentParser(description="Render AltStore news promo image")
    ap.add_argument("--name", help="app display name (default: news.toml)")
    ap.add_argument("--tagline", help="short one-line descriptor (default: news.toml)")
    ap.add_argument("--icon", default="icon.png", help="icon path, relative to --out dir")
    ap.add_argument("--tint", help="badge/glow accent color (default: config.toml [app] tint_color)")
    ap.add_argument("--tint-alt", help="secondary accent color (default: config.toml [source] tint_color)")
    ap.add_argument("--out", required=True, help="output directory (the app folder, e.g. PiliPlus)")
    args = ap.parse_args()

    out = Path(args.out)
    news, cfg = load_configs(out)
    colors = news.get("colors", {}) or {}

    name = args.name or news.get("name")
    if not name:
        sys.exit("error: no app name (pass --name or set name in news.toml)")
    tagline = args.tagline or news.get("tagline") or ""

    app_tint = (cfg.get("app", {}) or {}).get("tint_color")
    src_tint = (cfg.get("source", {}) or {}).get("tint_color")
    tint = args.tint or colors.get("tint") or app_tint or "#73B480"
    tint_alt = args.tint_alt or colors.get("tint_alt") or src_tint or tint

    # Background: explicit news.toml value, else a light shade derived from
    # the app icon's dominant color, else a dark tint-derived base. The
    # gradient stops, name color and tagline color derive from it (each
    # stop can be pinned individually in news.toml).
    bg = colors.get("background")
    if bg is None:
        icon_color = extract_icon_color(out / args.icon)
        bg = derive_light_background(icon_color) if icon_color else derive_background(tint)
    bg = check_hex(bg, "background")
    derived_mid, derived_dark = derive_bg_stops(bg)
    bg_mid = check_hex(colors.get("bg_mid") or derived_mid, "bg_mid")
    bg_dark = check_hex(colors.get("bg_dark") or derived_dark, "bg_dark")
    text_color = check_hex(colors.get("text_color") or auto_text_color(bg), "text_color")
    tagline_color = check_hex(
        colors.get("tagline_color") or derive_tagline_color(bg), "tagline_color"
    )

    # Layout the right column: the name's cap top lines up with the icon's
    # top edge, and the description (possibly several wrapped lines) is sized
    # so its bottom stays above the NEW UPDATE badge's bottom edge.
    name_font = fit_name_font(name)
    ascent_em = measure_font_ascent_em(800) or CAP_HEIGHT_FACTOR
    name_y = ICON_Y + ascent_em * name_font
    name_bottom = name_y + 0.25 * name_font  # descender, conservative
    desc_space = BADGE_BOTTOM - name_bottom - GAP_DESC

    tag_lines, tagline_font = fit_tagline(tagline, desc_space)
    line_h_tag = 1.5 * tagline_font
    tag_ys = [
        name_bottom + GAP_DESC + (i + 0.8) * line_h_tag for i in range(len(tag_lines))
    ]

    tokens = {
        "{{APP_NAME}}": escape(name),
        "{{APP_NAME_SIZE}}": str(name_font),
        "{{NAME_Y}}": f"{name_y:.0f}",
        "{{TAGLINE_LINES}}": build_tagline_lines(
            tag_lines, tag_ys, tagline_font, tagline_color
        ),
        "{{ICON}}": args.icon,
        "{{TINT}}": check_hex(tint, "tint"),
        "{{TINT_ALT}}": check_hex(tint_alt, "tint_alt"),
        "{{BG_COLOR}}": bg,
        "{{BG_COLOR_MID}}": bg_mid,
        "{{BG_COLOR_DARK}}": bg_dark,
        "{{NAME_COLOR}}": text_color,
        "{{TAGLINE_COLOR}}": tagline_color,
    }

    svg = TEMPLATE.read_text(encoding="utf-8")
    for token, value in tokens.items():
        svg = svg.replace(token, value)

    leftover = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", svg)))
    if leftover:
        sys.exit(f"error: unresolved template tokens: {leftover}")

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
