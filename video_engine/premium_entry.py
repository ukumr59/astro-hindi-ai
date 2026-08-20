"""AstroPratidin premium presentation layer.

The premium renderer owns presentation only. Audio timing and scene order stay
owned by render_sync.py. The channel logo is always the bundled master asset;
no logo is redrawn, retyped, recolored, or replaced by a look-alike.
"""
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageOps

from . import render_sync as base

BRAND = "AstroPratidin"
GOLD = (247, 202, 77, 255)
GOLD_SOFT = (255, 226, 125, 210)
CREAM = (255, 244, 214, 255)
DARK = (25, 7, 34, 245)
BRAND_LOGO = Path(__file__).resolve().parents[1] / "assets" / "brand" / "astropratidin_logo.webp"


def _require_brand_asset():
    if not BRAND_LOGO.exists():
        raise RuntimeError(f"Missing master AstroPratidin brand asset: {BRAND_LOGO}")


def _brand_logo(canvas, x=48, y=64, size=118):
    """Composite the exact bundled master logo; never redraw a substitute."""
    _require_brand_asset()
    with Image.open(BRAND_LOGO) as source:
        logo = ImageOps.contain(source.convert("RGBA"), (size, size), Image.Resampling.LANCZOS)
    px = x + (size - logo.width) // 2
    py = y + (size - logo.height) // 2
    canvas.alpha_composite(logo, (px, py))


def _panel(draw, box, radius=28, fill=DARK, outline=GOLD, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _short_cues(narration):
    text = base.clean(narration)
    parts = [base.clean(x) for x in re.split(r"(?<=[।!?])\s+", text) if base.clean(x)]
    if parts and re.match(r"^\S+ राशि[।:]", parts[0]):
        parts = parts[1:]
    cues = []
    for part in parts:
        part = re.sub(r"^(आज का दिन कुल मिलाकर|आज)\s+", "", part).strip()
        if len(part) > 62:
            part = part[:59].rsplit(" ", 1)[0] + "..."
        if part and part not in cues:
            cues.append(part)
        if len(cues) == 3:
            break
    defaults = ["काम और अवसर", "धन में संतुलन", "रिश्तों में संवाद"]
    while len(cues) < 3:
        cues.append(defaults[len(cues)])
    return cues


def _tone(narration):
    if "सावधानी" in narration or "जल्दबाजी" in narration:
        return "सावधानी रखें"
    if "अनुकूल" in narration or "अवसर" in narration:
        return "अनुकूल संकेत"
    return "मिश्रित संकेत"


def _save(canvas, path):
    canvas.convert("RGB").save(path, "JPEG", quality=98, subsampling=0)
    return path


def premium_intro(script):
    out = base.SCENES / "000_intro.jpg"
    source = ImageOps.exif_transpose(Image.open(base.INTRO_ASSET).convert("RGB"))
    canvas = base.background()
    hero_h = 1000
    hero = base.crop_cover(source, base.W - 64, hero_h)
    canvas.alpha_composite(hero.convert("RGBA"), (32, 48))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((20, 20, base.W - 20, base.H - 20), radius=46, outline=GOLD, width=4)
    draw.rounded_rectangle((32, 48, base.W - 32, hero_h + 48), radius=36, outline=(247, 202, 77, 180), width=2)
    _brand_logo(canvas, 48, 66, 128)

    title = "दैनिक वैदिक ज्योतिष"
    f = base.fit(draw, title, base.W - 120, 58, 38)
    b = draw.textbbox((0, 0), title, font=f)
    draw.text(((base.W - (b[2] - b[0])) / 2, 1090), title, font=f, fill=CREAM)

    date = next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")), "आज का दैनिक राशिफल")
    f = base.fit(draw, date, base.W - 150, 33, 22)
    _panel(draw, (55, 1160, base.W - 55, 1240), radius=25)
    b = draw.textbbox((0, 0), date, font=f)
    draw.text(((base.W - (b[2] - b[0])) / 2, 1180), date, font=f, fill=CREAM)

    transition = next((x.strip() for x in script.splitlines() if "गोचर" in x or "प्रवेश" in x), "आज के प्रमुख ग्रह गोचर के संकेत")
    _panel(draw, (55, 1260, base.W - 55, 1480), radius=30)
    f = base.fit(draw, "आज का प्रमुख गोचर", base.W - 120, 30, 22)
    b = draw.textbbox((0, 0), "आज का प्रमुख गोचर", font=f)
    draw.text(((base.W - (b[2] - b[0])) / 2, 1285), "आज का प्रमुख गोचर", font=f, fill=GOLD)
    y = 1338
    for line in base.wrap(transition, 48)[:3]:
        f = base.fit(draw, line, base.W - 130, 27, 19)
        b = draw.textbbox((0, 0), line, font=f)
        draw.text(((base.W - (b[2] - b[0])) / 2, y), line, font=f, fill=CREAM)
        y += 43

    f = base.fit(draw, "बारहों राशियों के लिए आज के ग्रह संकेत", base.W - 100, 27, 19)
    b = draw.textbbox((0, 0), "बारहों राशियों के लिए आज के ग्रह संकेत", font=f)
    draw.text(((base.W - (b[2] - b[0])) / 2, 1575), "बारहों राशियों के लिए आज के ग्रह संकेत", font=f, fill=GOLD_SOFT)
    return _save(canvas, out)


def premium_rashi(index, key, label, deity, image_path, narration):
    out = base.SCENES / f"{index:03d}_{key}.jpg"
    canvas = base.background()
    draw = ImageDraw.Draw(canvas)

    with Image.open(image_path) as im:
        deity_img = ImageOps.exif_transpose(im.convert("RGB"))
    base.put_hero(canvas, deity_img, (32, 48, base.W - 32, 1018), radius=36)
    draw.rounded_rectangle((32, 48, base.W - 32, 1018), radius=36, outline=GOLD, width=3)
    _brand_logo(canvas, 48, 66, 112)

    _panel(draw, (40, 1048, base.W - 40, 1835), radius=36, fill=(25, 7, 34, 250), outline=(247, 202, 77, 205), width=2)
    badge = f"{index:02d}  {label}"
    f = base.fit(draw, badge, base.W - 140, 44, 28)
    b = draw.textbbox((0, 0), badge, font=f)
    draw.text(((base.W - (b[2] - b[0])) / 2, 1082), badge, font=f, fill=CREAM)
    draw.line((105, 1145, base.W - 105, 1145), fill=(247, 202, 77, 150), width=2)

    tone = _tone(narration)
    f = base.fit(draw, tone, 300, 25, 19)
    b = draw.textbbox((0, 0), tone, font=f)
    pill_w = b[2] - b[0] + 52
    px = (base.W - pill_w) / 2
    _panel(draw, (px, 1172, px + pill_w, 1232), radius=25, fill=(55, 21, 52, 245), outline=GOLD, width=2)
    draw.text((px + 26, 1185), tone, font=f, fill=GOLD)

    cues = _short_cues(narration)
    y = 1270
    for i, cue in enumerate(cues):
        draw.ellipse((72, y + 14, 84, y + 26), fill=GOLD)
        f = base.fit(draw, cue, base.W - 170, 29, 20)
        b = draw.textbbox((0, 0), cue, font=f)
        draw.text(((base.W - (b[2] - b[0])) / 2 + 10, y), cue, font=f, fill=CREAM)
        if i < len(cues) - 1:
            draw.line((90, y + 72, base.W - 90, y + 72), fill=(247, 202, 77, 85), width=1)
        y += 105

    draw.line((105, 1600, base.W - 105, 1600), fill=(247, 202, 77, 120), width=1)
    prompt = "विस्तृत फलादेश आवाज़ में सुनें"
    f = base.fit(draw, prompt, base.W - 100, 25, 18)
    b = draw.textbbox((0, 0), prompt, font=f)
    draw.text(((base.W - (b[2] - b[0])) / 2, 1640), prompt, font=f, fill=GOLD_SOFT)
    return _save(canvas, out)


def premium_outro():
    out = base.SCENES / "013_outro.jpg"
    canvas = base.background()
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((20, 20, base.W - 20, base.H - 20), radius=46, outline=GOLD, width=4)
    _brand_logo(canvas, 402, 250, 276)

    title = "शुभम् भवतु"
    f = base.fit(draw, title, base.W - 160, 64, 42)
    b = draw.textbbox((0, 0), title, font=f)
    draw.text(((base.W - (b[2] - b[0])) / 2, 590), title, font=f, fill=CREAM)

    lines = ["आपका दिन शुभ और मंगलमय हो", "ईश्वर की कृपा और सकारात्मक ऊर्जा आपके साथ रहे", "कल फिर मिलेंगे नए ग्रह संकेतों के साथ"]
    y = 790
    for line in lines:
        f = base.fit(draw, line, base.W - 180, 34, 24)
        b = draw.textbbox((0, 0), line, font=f)
        draw.text(((base.W - (b[2] - b[0])) / 2, y), line, font=f, fill=CREAM)
        y += 78

    f = base.fit(draw, BRAND, base.W - 160, 24, 18)
    b = draw.textbbox((0, 0), BRAND, font=f)
    draw.text(((base.W - (b[2] - b[0])) / 2, 1170), BRAND, font=f, fill=GOLD_SOFT)
    return _save(canvas, out)


def premium_motion(ffmpeg, scene, seconds, index):
    out = base.SCENES / f"motion_{index:02d}.mp4"
    seconds = max(0.5, float(seconds))
    fade = min(0.28, max(0.12, seconds / 8))
    start = max(0.05, seconds - fade)
    sw = base.W * 110 // 100 // 2 * 2
    sh = base.H * 110 // 100 // 2 * 2
    vf = (f"scale={sw}:{sh}:force_original_aspect_ratio=disable,"
          f"crop={base.W}:{base.H}:x=(in_w-out_w)/2:y=(in_h-out_h)/2,"
          f"fps={base.FPS},fade=t=in:st=0:d={fade:.3f},fade=t=out:st={start:.3f}:d={fade:.3f}")
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
