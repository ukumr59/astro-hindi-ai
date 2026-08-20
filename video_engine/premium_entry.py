"""AstroPratidin premium presentation layer.

Design rules:
- Audio timing remains owned by render_sync.py.
- One clean, correctly oriented deity image per rashi scene.
- Real circular brand treatment drawn as a compact vector-like mark.
- No unsupported Unicode ornaments (prevents missing-glyph squares).
- No stacked card/box overload; information is presented as one coherent panel.
"""
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from . import render_sync as base

BRAND = "AstroPratidin"
TAGLINE = "दैनिक वैदिक ज्योतिष"
GOLD = (247, 202, 77, 255)
GOLD_SOFT = (255, 226, 125, 210)
CREAM = (255, 244, 214, 255)
DARK = (25, 7, 34, 245)
BLUE = (13, 36, 92, 255)
WINE = (43, 10, 34, 255)


def _rounded_text_panel(d, box, radius=28, fill=DARK, outline=GOLD, width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _brand_logo(canvas, x=46, y=64, size=118):
    """Clean circular AstroPratidin mark.

    Only characters known to be safe in the bundled font are used. Decorative
    elements are drawn as shapes, not Unicode symbols, so no tofu/square glyphs
    can appear in the rendered video.
    """
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((1, 1, size - 2, size - 2), fill=BLUE, outline=GOLD, width=4)
    d.ellipse((9, 9, size - 10, size - 10), outline=GOLD_SOFT, width=2)

    # Sun/star emblem, drawn rather than represented by a Unicode character.
    cx, cy = size // 2, int(size * .28)
    d.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=GOLD)
    for dx, dy in ((0,-25),(0,25),(-25,0),(25,0),(-18,-18),(18,-18),(-18,18),(18,18)):
        d.line((cx, cy, cx + dx, cy + dy), fill=GOLD_SOFT, width=2)

    bf = base.fit(d, BRAND, size - 18, max(15, int(size * .145)), 11)
    b = d.textbbox((0, 0), BRAND, font=bf)
    d.text(((size - (b[2]-b[0])) / 2, int(size * .45)), BRAND, font=bf, fill=CREAM)

    tf = base.fit(d, TAGLINE, size - 14, max(10, int(size * .085)), 8)
    b = d.textbbox((0, 0), TAGLINE, font=tf)
    d.text(((size - (b[2]-b[0])) / 2, int(size * .72)), TAGLINE, font=tf, fill=GOLD_SOFT)
    canvas.alpha_composite(layer, (x, y))


def _particles(canvas, seed, count=22):
    import random
    rng = random.Random(seed)
    d = ImageDraw.Draw(canvas)
    for _ in range(count):
        x = rng.randint(45, base.W - 45)
        y = rng.randint(45, base.H - 45)
        r = rng.choice((1, 1, 1, 2))
        d.ellipse((x-r, y-r, x+r, y+r), fill=(247, 202, 77, rng.randint(35, 90)))


def _short_cues(narration):
    text = base.clean(narration)
    parts = [base.clean(x) for x in re.split(r"(?<=[।!?])\s+", text) if base.clean(x)]
    if parts and re.match(r"^\S+ राशि[।:]", parts[0]):
        parts = parts[1:]
    cues = []
    for p in parts:
        p = re.sub(r"^(आज का दिन कुल मिलाकर|आज)\s+", "", p).strip()
        if len(p) > 62:
            p = p[:59].rsplit(" ", 1)[0] + "..."
        if p and p not in cues:
            cues.append(p)
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


def premium_intro(script):
    out = base.SCENES / "000_intro.jpg"
    source = ImageOps.exif_transpose(Image.open(base.INTRO_ASSET).convert("RGB"))
    canvas = base.background()

    # One image only: no mirrored/blurred duplicate.
    hero_h = 1000
    hero = base.crop_cover(source, base.W - 64, hero_h)
    canvas.alpha_composite(hero.convert("RGBA"), (32, 48))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((20, 20, base.W - 20, base.H - 20), radius=46, outline=GOLD, width=4)
    d.rounded_rectangle((32, 48, base.W - 32, hero_h + 48), radius=36, outline=(247, 202, 77, 180), width=2)
    _brand_logo(canvas, 48, 68, 128)

    title = "॥ दैनिक वैदिक ज्योतिष ॥"
    f = base.fit(d, title, base.W - 120, 58, 38)
    b = d.textbbox((0, 0), title, font=f)
    d.text(((base.W - (b[2]-b[0])) / 2, 1090), title, font=f, fill=CREAM)

    date = next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")), "आज का दैनिक राशिफल")
    f = base.fit(d, date, base.W - 150, 33, 22)
    _rounded_text_panel(d, (55, 1160, base.W - 55, 1240), radius=25)
    b = d.textbbox((0, 0), date, font=f)
    d.text(((base.W-(b[2]-b[0]))/2, 1180), date, font=f, fill=CREAM)

    transition = next((x.strip() for x in script.splitlines() if "गोचर" in x or "प्रवेश" in x), "आज के प्रमुख ग्रह गोचर के संकेत")
    _rounded_text_panel(d, (55, 1260, base.W - 55, 1480), radius=30)
    hf = base.fit(d, "आज का प्रमुख गोचर", base.W - 120, 30, 22)
    b = d.textbbox((0, 0), "आज का प्रमुख गोचर", font=hf)
    d.text(((base.W-(b[2]-b[0]))/2, 1285), "आज का प्रमुख गोचर", font=hf, fill=GOLD)
    y = 1338
    for line in base.wrap(transition, 48)[:3]:
        lf = base.fit(d, line, base.W - 130, 27, 19)
        b = d.textbbox((0, 0), line, font=lf)
        d.text(((base.W-(b[2]-b[0]))/2, y), line, font=lf, fill=CREAM)
        y += 43

    sub = "बारहों राशियों के लिए आज के ग्रह संकेत"
    sf = base.fit(d, sub, base.W - 100, 27, 19)
    b = d.textbbox((0, 0), sub, font=sf)
    d.text(((base.W-(b[2]-b[0]))/2, 1575), sub, font=sf, fill=GOLD_SOFT)
    return _save(canvas, out)


def premium_rashi(index, key, label, deity, image_path, narration):
    out = base.SCENES / f"{index:03d}_{key}.jpg"
    canvas = base.background()
    d = ImageDraw.Draw(canvas)

    # Dominant, single, correctly oriented deity image.
    with Image.open(image_path) as im:
        deity_img = ImageOps.exif_transpose(im.convert("RGB"))
    base.put_hero(canvas, deity_img, (32, 48, base.W - 32, 1018), radius=36)
    d.rounded_rectangle((32, 48, base.W - 32, 1018), radius=36, outline=GOLD, width=3)
    _brand_logo(canvas, 48, 66, 112)

    # Single coherent lower information panel.
    _rounded_text_panel(d, (40, 1048, base.W - 40, 1835), radius=36, fill=(25,7,34,250), outline=(247,202,77,205), width=2)

    badge = f"{index:02d}  {label}"
    bf = base.fit(d, badge, base.W - 140, 44, 28)
    b = d.textbbox((0, 0), badge, font=bf)
    d.text(((base.W-(b[2]-b[0]))/2, 1082), badge, font=bf, fill=CREAM)
    d.line((105, 1145, base.W - 105, 1145), fill=(247,202,77,150), width=2)

    tone = _tone(narration)
    tf = base.fit(d, tone, 300, 25, 19)
    b = d.textbbox((0, 0), tone, font=tf)
    pill_w = (b[2]-b[0]) + 52
    px = (base.W - pill_w) / 2
    _rounded_text_panel(d, (px, 1172, px + pill_w, 1232), radius=25, fill=(55,21,52,245), outline=GOLD, width=2)
    d.text((px + 26, 1185), tone, font=tf, fill=GOLD)

    # Three concise highlights, visually separated by hairlines rather than boxes.
    cues = _short_cues(narration)
    y = 1270
    for i, cue in enumerate(cues):
        d.ellipse((72, y + 14, 84, y + 26), fill=GOLD)
        pf = base.fit(d, cue, base.W - 170, 29, 20)
        b = d.textbbox((0, 0), cue, font=pf)
        d.text(((base.W-(b[2]-b[0]))/2 + 10, y), cue, font=pf, fill=CREAM)
        if i < len(cues) - 1:
            d.line((90, y + 72, base.W - 90, y + 72), fill=(247,202,77,85), width=1)
        y += 105

    d.line((105, 1600, base.W - 105, 1600), fill=(247,202,77,120), width=1)
    prompt = "विस्तृत फलादेश आवाज़ में सुनें"
    pf = base.fit(d, prompt, base.W - 100, 25, 18)
    b = d.textbbox((0, 0), prompt, font=pf)
    d.text(((base.W-(b[2]-b[0]))/2, 1640), prompt, font=pf, fill=GOLD_SOFT)

    # Small channel signature, not another logo badge.
    sf = base.fit(d, BRAND, base.W - 100, 22, 16)
    b = d.textbbox((0, 0), BRAND, font=sf)
    d.text(((base.W-(b[2]-b[0]))/2, 1745), BRAND, font=sf, fill=(255,244,214,190))
    return _save(canvas, out)


def _save(canvas, out):
    canvas.convert("RGB").save(out, "JPEG", quality=98, subsampling=0)
    return out


def premium_motion(ffmpeg, scene, seconds, index):
    # Keep motion subtle and deterministic; avoid zoompan/filter syntax entirely.
    out = base.SCENES / f"motion_{index:02d}.mp4"
    seconds = max(.5, float(seconds))
    fade = min(.28, max(.12, seconds / 8))
    start = max(.05, seconds - fade)
    sw = base.W * 110 // 100 // 2 * 2
    sh = base.H * 110 // 100 // 2 * 2
    vf = (
        f"scale={sw}:{sh}:force_original_aspect_ratio=disable,"
        f"crop={base.W}:{base.H}:x=(in_w-out_w)/2:y=(in_h-out_h)/2,"
        f"fps={base.FPS},fade=t=in:st=0:d={fade:.3f},fade=t=out:st={start:.3f}:d={fade:.3f}"
    )
    base.run([ffmpeg, "-y", "-loop", "1", "-i", scene, "-vf", vf,
              "-t", f"{seconds:.3f}", "-an", "-c:v", "libx264",
              "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out], 900)
    return out


def main():
    base.intro = premium_intro
    base.rashi_scene = premium_rashi
    base.motion = premium_motion
    base.main()


if __name__ == "__main__":
    main()
