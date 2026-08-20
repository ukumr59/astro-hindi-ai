"""V20 production entry point.

V20 has one non-negotiable branding rule: the approved AstroPratidin master
logo is rendered by the protected brand header and MUST NOT be baked into any
background/intro artwork. The legacy intro_devotional.jpg contained an old
embedded logo, so V20 replaces that intro with a clean generated composition.
"""
from pathlib import Path

from PIL import ImageDraw

from . import premium_entry as premium

ROOT = Path(__file__).resolve().parents[1]
APPROVED_LOGO = ROOT / "assets" / "brand" / "astropratidin_logo_256.png"

if not APPROVED_LOGO.exists():
    raise RuntimeError(f"Approved AstroPratidin master logo missing: {APPROVED_LOGO}")

# Use the exact supplied master logo everywhere the renderer places branding.
premium.BRAND_LOGO = APPROVED_LOGO


def v20_intro(script):
    """Generate a clean intro with NO baked-in logo or legacy artwork.

    The only AstroPratidin logo in the scene is premium._brand_header(), which
    uses the approved master asset. This prevents the old circular emblem from
    reappearing inside the artwork.
    """
    out = premium.base.SCENES / "000_intro.jpg"
    canvas = premium.base.background()
    draw = ImageDraw.Draw(canvas)
    premium._frame(draw)
    premium._brand_header(canvas, draw)

    # Clean, abstract celestial backdrop. No external artwork and no embedded
    # branding are used here, so the master logo cannot be duplicated.
    for r, alpha in [(420, 42), (330, 32), (240, 24)]:
        draw.ellipse(
            (premium.base.W // 2 - r, 420 - r,
             premium.base.W // 2 + r, 420 + r),
            outline=(247, 202, 77, alpha), width=2
        )
    draw.line((150, 420, premium.base.W - 150, 420), fill=(247, 202, 77, 75), width=2)
    draw.line((premium.base.W // 2, 250, premium.base.W // 2, 780),
              fill=(247, 202, 77, 55), width=2)

    premium._panel(
        draw,
        (premium.PAGE_MARGIN, 820, premium.base.W - premium.PAGE_MARGIN, premium.CONTENT_BOTTOM),
        radius=36,
    )
    premium._text(draw, "दैनिक वैदिक ज्योतिष", 900, premium.base.W - 180, 54,
                  premium.CREAM, minimum=34)

    date = next(
        (x.strip() for x in script.splitlines() if x.strip().startswith("आज ")),
        "आज का दैनिक राशिफल",
    )
    premium._panel(draw, (72, 1010, premium.base.W - 72, 1100),
                   radius=24, fill=premium.PANEL_ALT)
    premium._text(draw, date, 1032, premium.base.W - 180, 26,
                  premium.CREAM, minimum=19)

    transition = next(
        (x.strip() for x in script.splitlines() if "गोचर" in x or "प्रवेश" in x),
        "आज के प्रमुख ग्रह गोचर के संकेत",
    )
    premium._panel(draw, (72, 1140, premium.base.W - 72, 1435),
                   radius=28, fill=premium.PANEL_ALT)
    premium._text(draw, "आज के प्रमुख ग्रह गोचर", 1165,
                  premium.base.W - 160, 30, premium.GOLD, minimum=22)
    y = 1230
    for line in premium.base.wrap(transition, 48)[:4]:
        premium._text(draw, line, y, premium.base.W - 170, 23,
                      premium.CREAM, minimum=18)
        y += 48

    premium._text(draw, "बारहों राशियों के लिए आज के ग्रह संकेत", 1510,
                  premium.base.W - 150, 24, premium.GOLD_SOFT, minimum=18)
    premium._text(draw, "विस्तृत फलादेश आवाज़ में सुनें", 1630,
                  premium.base.W - 190, 22, premium.CREAM, minimum=18)
    return premium._save(canvas, out)


# Replace only the legacy intro. Rashi/outro rendering remains the approved
# premium renderer, preserving its existing audio/timeline behaviour.
premium.premium_intro = v20_intro

premium.main()
