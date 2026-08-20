"""AstroPratidin V18 presentation entry point.

Fixes the V17 Latin-glyph regression by never typesetting the English channel
name with the Devanagari-only production font. The exact master AstroPratidin
logo asset is used wherever the brand needs to appear.
"""
from pathlib import Path
from PIL import Image, ImageDraw

from . import premium_entry as v17
from . import render_sync as base

BRAND_LOGO = v17.BRAND_LOGO
GOLD = v17.GOLD
GOLD_SOFT = v17.GOLD_SOFT
CREAM = v17.CREAM


def premium_outro():
    out = base.SCENES / "013_outro.jpg"
    canvas = base.background()
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((20, 20, base.W - 20, base.H - 20), radius=46, outline=GOLD, width=4)

    # The master image is the only representation of the AstroPratidin name.
    # Do NOT typeset "AstroPratidin" with NotoSansDevanagari: that bundled font
    # intentionally contains Devanagari glyphs but not Latin glyphs.
    v17._brand_logo(canvas, 402, 250, 276)

    title = "शुभम् भवतु"
    f = base.fit(draw, title, base.W - 160, 64, 42)
    b = draw.textbbox((0, 0), title, font=f)
    draw.text(((base.W - (b[2] - b[0])) / 2, 590), title, font=f, fill=CREAM)

    lines = [
        "आपका दिन शुभ और मंगलमय हो",
        "ईश्वर की कृपा और सकारात्मक ऊर्जा आपके साथ रहे",
        "कल फिर मिलेंगे नए ग्रह संकेतों के साथ",
    ]
    y = 790
    for line in lines:
        f = base.fit(draw, line, base.W - 180, 34, 24)
        b = draw.textbbox((0, 0), line, font=f)
        draw.text(((base.W - (b[2] - b[0])) / 2, y), line, font=f, fill=CREAM)
        y += 78

    return v17._save(canvas, out)


def main():
    v17._require_brand_asset()
    base.intro = v17.premium_intro
    base.rashi_scene = v17.premium_rashi
    base.outro = premium_outro
    base.motion = v17.premium_motion
    base.main()


if __name__ == "__main__":
    main()
