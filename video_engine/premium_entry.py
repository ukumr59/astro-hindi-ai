"""AstroPratidin V19 premium renderer.

Design contract:
- The exact bundled AstroPratidin master logo is the only brand mark.
- Branding lives in a protected, consistent header zone on every scene.
- No brand name is retyped and no decorative Unicode glyphs are used.
- Hindi copy is rendered only with the bundled Devanagari font.
- The narration/audio timeline remains owned by render_sync.py.
"""
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageOps

from . import render_sync as base

GOLD = (247, 202, 77, 255)
GOLD_SOFT = (255, 226, 125, 255)
CREAM = (255, 246, 224, 255)
BG = (18, 5, 30, 255)
PANEL = (27, 8, 36, 252)
PANEL_ALT = (40, 13, 49, 252)
BRAND_LOGO = Path(__file__).resolve().parents[1] / "assets" / "brand" / "astropratidin_logo.webp"

# Fixed safe geometry for 1080x1920 output. The logo never touches artwork.
PAGE_MARGIN = 32
HEADER_TOP = 28
HEADER_BOTTOM = 238
HEADER_LOGO_SIZE = 190
HERO_TOP = 264
HERO_BOTTOM = 1040
CONTENT_TOP = 1070
CONTENT_BOTTOM = 1878


def _require_brand_asset():
    if not BRAND_LOGO.exists():
        raise RuntimeError(f"Missing master AstroPratidin brand asset: {BRAND_LOGO}")
    with Image.open(BRAND_LOGO) as im:
        if min(im.size) < 160:
            raise RuntimeError(f"Master logo is too small for production use: {im.size}")


def _logo(canvas, size=HEADER_LOGO_SIZE):
    """Place the exact master logo in the same protected header on every scene."""
    _require_brand_asset()
    with Image.open(BRAND_LOGO) as source:
        logo = ImageOps.contain(source.convert("RGBA"), (size, size), Image.Resampling.LANCZOS)
    x = (base.W - logo.width) // 2
    y = HEADER_TOP + (HEADER_BOTTOM - HEADER_TOP - logo.height) // 2
    canvas.alpha_composite(logo, (x, y))


def _frame(draw):
    draw.rounded_rectangle(
        (18, 18, base.W - 18, base.H - 18),
        radius=42, outline=GOLD, width=4
    )


def _brand_header(canvas, draw):
    """Dedicated logo-safe brand zone. Artwork begins below it."""
    draw.rounded_rectangle(
        (PAGE_MARGIN, HEADER_TOP, base.W - PAGE_MARGIN, HEADER_BOTTOM),
        radius=34, fill=(24, 7, 34, 255), outline=(247, 202, 77, 210), width=2
    )
    # Two understated divider lines create a premium header without competing
    # with the master logo.
    draw.line((150, HEADER_BOTTOM - 12, base.W - 150, HEADER_BOTTOM - 12),
              fill=(247, 202, 77, 90), width=1)
    _logo(canvas)


def _panel(draw, box, radius=32, fill=PANEL, outline=(247, 202, 77, 190), width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _text(draw, text, y, max_width, size=28, fill=CREAM, center=True, minimum=18):
    """Safe Hindi text draw with measured width and deterministic placement."""
    f = base.fit(draw, text, max_width, size, minimum)
    b = draw.textbbox((0, 0), text, font=f)
    width = b[2] - b[0]
    x = (base.W - width) / 2 if center else 70
    draw.text((x, y), text, font=f, fill=fill)
    return b[3] - b[1]


def _wrap_sentences(text, max_chars=58, max_items=3):
    clean = base.clean(text)
    parts = [base.clean(x) for x in re.split(r"(?<=[।!?])\s+", clean) if base.clean(x)]
    # Remove the repeated rashi heading from the visual copy.
    if parts and re.match(r"^\S+ राशि[।:]", parts[0]):
        parts = parts[1:]
    result = []
    for part in parts:
        part = re.sub(r"^(आज का दिन कुल मिलाकर|आज)\s+", "", part).strip()
        if len(part) > max_chars:
            part = part[: max_chars - 1].rsplit(" ", 1)[0] + "…"
        if part and part not in result:
            result.append(part)
        if len(result) >= max_items:
            break
    return result


def _tone(narration):
    if "सावधानी" in narration or "जल्दबाजी" in narration:
        return "सावधानी रखें"
    if "अनुकूल" in narration or "अवसर" in narration:
        return "अनुकूल संकेत"
    return "संतुलित संकेत"


def _save(canvas, path):
    canvas.convert("RGB").save(path, "JPEG", quality=98, subsampling=0)
    return path


def _hero(canvas, image_path):
    with Image.open(image_path) as im:
        deity = ImageOps.exif_transpose(im.convert("RGB"))
    base.put_hero(canvas, deity, (PAGE_MARGIN, HERO_TOP, base.W - PAGE_MARGIN, HERO_BOTTOM), radius=34)


def premium_intro(script):
    out = base.SCENES / "000_intro.jpg"
    source = ImageOps.exif_transpose(Image.open(base.INTRO_ASSET).convert("RGB"))
    canvas = base.background()
    draw = ImageDraw.Draw(canvas)
    _frame(draw)
    _brand_header(canvas, draw)

    hero = base.crop_cover(source, base.W - 2 * PAGE_MARGIN, HERO_BOTTOM - HERO_TOP)
    mask = Image.new("L", hero.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, hero.width - 1, hero.height - 1), radius=34, fill=255)
    canvas.paste(hero, (PAGE_MARGIN, HERO_TOP), mask)
    draw.rounded_rectangle((PAGE_MARGIN, HERO_TOP, base.W - PAGE_MARGIN, HERO_BOTTOM), radius=34, outline=GOLD, width=3)

    _panel(draw, (PAGE_MARGIN, CONTENT_TOP, base.W - PAGE_MARGIN, CONTENT_BOTTOM), radius=34)
    _text(draw, "दैनिक वैदिक ज्योतिष", 1100, base.W - 140, 46, CREAM, minimum=30)

    date = next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")), "आज का दैनिक राशिफल")
    _panel(draw, (72, 1180, base.W - 72, 1260), radius=24, fill=PANEL_ALT)
    _text(draw, date, 1198, base.W - 180, 24, CREAM, minimum=18)

    transition = next((x.strip() for x in script.splitlines() if "गोचर" in x or "प्रवेश" in x), "आज के प्रमुख ग्रह गोचर के संकेत")
    _panel(draw, (72, 1290, base.W - 72, 1510), radius=28, fill=PANEL_ALT)
    _text(draw, "आज के प्रमुख ग्रह गोचर", 1312, base.W - 160, 27, GOLD, minimum=21)
    y = 1370
    for line in base.wrap(transition, 48)[:3]:
        _text(draw, line, y, base.W - 170, 22, CREAM, minimum=18)
        y += 42
    _text(draw, "बारहों राशियों के लिए आज के ग्रह संकेत", 1590, base.W - 150, 22, GOLD_SOFT, minimum=18)
    return _save(canvas, out)


def premium_rashi(index, key, label, deity, image_path, narration):
    out = base.SCENES / f"{index:03d}_{key}.jpg"
    canvas = base.background()
    draw = ImageDraw.Draw(canvas)
    _frame(draw)
    _brand_header(canvas, draw)
    _hero(canvas, image_path)

    _panel(draw, (PAGE_MARGIN, CONTENT_TOP, base.W - PAGE_MARGIN, CONTENT_BOTTOM), radius=34)

    # Strong, consistent title band.
    _panel(draw, (64, 1092, base.W - 64, 1180), radius=24, fill=PANEL_ALT)
    _text(draw, f"{index:02d}  {label}", 1115, base.W - 180, 34, CREAM, minimum=24)

    tone = _tone(narration)
    tone_w = 340
    tone_font = base.fit(draw, tone, tone_w, 22, 18)
    tb = draw.textbbox((0, 0), tone, font=tone_font)
    pill_w = min(420, (tb[2] - tb[0]) + 54)
    px = (base.W - pill_w) / 2
    _panel(draw, (px, 1210, px + pill_w, 1272), radius=22, fill=(53, 19, 53, 255), outline=GOLD, width=2)
    draw.text((px + (pill_w - (tb[2] - tb[0])) / 2, 1228), tone, font=tone_font, fill=GOLD)

    cues = _wrap_sentences(narration, max_chars=58, max_items=3)
    y = 1318
    row_h = 112
    for i in range(3):
        cue = cues[i] if i < len(cues) else ["काम और अवसर", "धन में संतुलन", "रिश्तों में संवाद"][i]
        # Draw the bullet as geometry, never as a font glyph.
        draw.ellipse((78, y + 17, 94, y + 33), fill=GOLD)
        f = base.fit(draw, cue, base.W - 180, 24, 18)
        b = draw.textbbox((0, 0), cue, font=f)
        tx = (base.W - (b[2] - b[0])) / 2 + 10
        draw.text((tx, y), cue, font=f, fill=CREAM)
        if i < 2:
            draw.line((92, y + 74, base.W - 92, y + 74), fill=(247, 202, 77, 75), width=1)
        y += row_h

    draw.line((150, 1668, base.W - 150, 1668), fill=(247, 202, 77, 100), width=1)
    _text(draw, "विस्तृत फलादेश आवाज़ में सुनें", 1710, base.W - 220, 23, GOLD_SOFT, minimum=18)
    _text(draw, "आज के ग्रह संकेत", 1770, base.W - 260, 18, (235, 218, 190, 255), minimum=16)
    return _save(canvas, out)


def premium_outro():
    out = base.SCENES / "013_outro.jpg"
    canvas = base.background()
    draw = ImageDraw.Draw(canvas)
    _frame(draw)
    _brand_header(canvas, draw)

    _panel(draw, (PAGE_MARGIN, 300, base.W - PAGE_MARGIN, CONTENT_BOTTOM), radius=36)
    _text(draw, "शुभम् भवतु", 590, base.W - 160, 62, CREAM, minimum=42)
    draw.line((180, 700, base.W - 180, 700), fill=(247, 202, 77, 120), width=2)

    lines = [
        "आपका दिन शुभ और मंगलमय हो",
        "ईश्वर की कृपा और सकारात्मक ऊर्जा आपके साथ रहे",
        "कल फिर मिलेंगे नए ग्रह संकेतों के साथ",
    ]
    y = 810
    for line in lines:
        _text(draw, line, y, base.W - 190, 29, CREAM, minimum=21)
        y += 86

    _panel(draw, (90, 1170, base.W - 90, 1345), radius=28, fill=PANEL_ALT)
    _text(draw, "कल फिर मिलेंगे", 1205, base.W - 220, 28, GOLD, minimum=21)
    _text(draw, "नए ग्रह संकेतों के साथ", 1260, base.W - 220, 24, CREAM, minimum=19)
    return _save(canvas, out)


def premium_motion(ffmpeg, scene, seconds, index):
    out = base.SCENES / f"motion_{index:02d}.mp4"
    seconds = max(0.5, float(seconds))
    fade = min(0.28, max(0.12, seconds / 8))
    start = max(0.05, seconds - fade)
    sw = base.W * 108 // 100 // 2 * 2
    sh = base.H * 108 // 100 // 2 * 2
    vf = (
        f"scale={sw}:{sh}:force_original_aspect_ratio=disable,"
        f"crop={base.W}:{base.H}:x=(in_w-out_w)/2:y=(in_h-out_h)/2,"
        f"fps={base.FPS},fade=t=in:st=0:d={fade:.3f},"
        f"fade=t=out:st={start:.3f}:d={fade:.3f}"
    )
    base.run([ffmpeg, "-y", "-loop", "1", "-i", scene, "-vf", vf,
              "-t", f"{seconds:.3f}", "-an", "-c:v", "libx264",
              "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out], 900)
    return out


def main():
    _require_brand_asset()
    base.intro = premium_intro
    base.rashi_scene = premium_rashi
    base.outro = premium_outro
    base.motion = premium_motion
    base.main()


if __name__ == "__main__":
    main()
