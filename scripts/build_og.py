"""Render the 1200x630 Open Graph card and the favicon.

Generated rather than drawn so the counts on it can never disagree with the
dataset — a share card claiming a branch count the site does not have is the
kind of small dishonesty that costs trust.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "og.png"
ICO = ROOT / "site" / "favicon.ico"

BG = (15, 23, 42)
FG = (248, 250, 252)
MUTED = (154, 171, 199)
ACCENT = (34, 197, 94)
INFO = (96, 165, 250)
WARN = (251, 191, 36)
LINE = (43, 58, 92)

MONO = "/System/Library/Fonts/Menlo.ttc"
MONO_BOLD = "/System/Library/Fonts/Menlo.ttc"
SANS = "/System/Library/Fonts/Supplemental/Arial.ttf"


def font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=index)


def main() -> None:
    counts = json.loads((ROOT / "data" / "banks.json").read_text())["counts"]

    img = Image.new("RGB", (1200, 630), BG)
    d = ImageDraw.Draw(img)

    for y in range(0, 630, 42):
        d.line([(0, y), (1200, y)], fill=(23, 32, 58), width=1)

    d.ellipse([72, 66, 92, 86], fill=ACCENT)
    d.text((108, 64), "bd-bank-routing", font=font(MONO_BOLD, 27, 1), fill=FG)

    d.text((72, 146), "Bangladesh bank", font=font(MONO_BOLD, 68, 1), fill=FG)
    d.text((72, 224), "routing numbers,", font=font(MONO_BOLD, 68, 1), fill=FG)
    d.text((72, 302), "with the receipts.", font=font(MONO_BOLD, 68, 1), fill=ACCENT)

    # The anatomy strip — the one idea worth putting on a share card.
    x, y = 72, 418
    segs = [("225", ACCENT, "BANK"), ("15", INFO, "DISTRICT"), ("013", WARN, "BRANCH"), ("5", MUTED, "CHECK")]
    fnum, flab = font(MONO_BOLD, 44, 1), font(MONO, 17)
    for text, colour, label in segs:
        w = d.textlength(text, font=fnum)
        d.rounded_rectangle([x, y, x + w + 34, y + 66], radius=9, outline=colour, width=2)
        d.text((x + 17, y + 8), text, font=fnum, fill=FG)
        d.text((x, y + 78), label, font=flab, fill=colour)
        x += w + 34 + 14

    d.line([(72, 548), (1128, 548)], fill=LINE, width=1)
    stats = (
        f"{counts['banks']} institutions  ·  {counts['branches']:,} branches  "
        f"·  all {counts['districts']} districts  ·  every row sourced and dated"
    )
    # Shrink to fit rather than trusting a hand-picked size: the counts grow, and
    # a card with its own tagline chopped off is worse than a slightly smaller one.
    size = 23
    while size > 14 and d.textlength(stats, font=font(MONO, size, 1)) > 1056:
        size -= 1
    d.text((72, 572), stats, font=font(MONO, size, 1), fill=MUTED)

    img.save(OUT, "PNG", optimize=True)
    print(f"  wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size / 1024:.0f} KB")

    # Browsers probe /favicon.ico whatever the markup says, and a 404 in the
    # console is a 404 in the console.
    icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    di = ImageDraw.Draw(icon)
    di.rounded_rectangle([0, 0, 255, 255], radius=56, fill=BG)
    di.ellipse([88, 88, 168, 168], fill=ACCENT)
    icon.save(ICO, "ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"  wrote {ICO.relative_to(ROOT)}  {ICO.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
