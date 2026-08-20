"""AstroPratidin V21 premium renderer.

Architecture goals:
- One immutable master AstroPratidin logo asset.
- One shared brand system for intro, rashi cards and outro.
- Data-driven rashi art direction from visual_profiles.py.
- Audio remains the master timeline in render_sync.py.
- Each rashi receives a distinct crop/motion treatment without changing
  approved source artwork.
- No legacy intro artwork, duplicate branding, or footer/footnote.
"""
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageOps
from . import render_sync as base
from .visual_profiles import RASHI_PROFILES, MOTION

ROOT = Path(__file__).resolve().parents[1]
MASTER_LOGO = ROOT / "assets" / "AstroPratidin Logo.png"
GOLD = (247, 202, 77, 255)
GOLD_SOFT = (255, 226, 125, 215)
CREAM = (255, 244, 214, 255)
DARK = (25, 7, 34, 255)
PANEL = (31, 9, 38, 248)
MUTED = (219, 202, 181, 225)


def _assert_brand_asset():
    if not MASTER_LOGO.exists():
        raise RuntimeError(f"Missing exact AstroPratidin master logo: {MASTER_LOGO}")
    with Image.open(MASTER_LOGO) as im:
        if min(im.size) < 200:
            raise RuntimeError(f"Master logo resolution too small: {im.size}")


def _load_master_logo(max_w, max_h):
    _assert_brand_asset()
    with Image.open(MASTER_LOGO) as src:
        src = ImageOps.exif_transpose(src).convert("RGBA")
        ratio = min(max_w / src.width, max_h / src.height)
        return src.resize((max(1, int(src.width * ratio)), max(1, int(src.height * ratio))), Image.Resampling.LANCZOS)


def _header(canvas):
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((28, 26, base.W - 28, 276), radius=34, fill=DARK, outline=GOLD, width=2)
    logo = _load_master_logo(230, 205)
    canvas.alpha_composite(logo, ((base.W-logo.width)//2, 42 + (205-logo.height)//2))
    d.line((100, 250, base.W - 100, 250), fill=(247, 202, 77, 110), width=1)


def _panel(d, box, radius=30, fill=PANEL):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=GOLD, width=2)


def _center_text(d, text, y, max_width, size, fill=CREAM, minimum=20):
    f = base.fit(d, text, max_width, size, minimum)
    b = d.textbbox((0, 0), text, font=f)
    d.text(((base.W-(b[2]-b[0]))/2, y), text, font=f, fill=fill)
    return f


def _short_cues(narration):
    parts = [base.clean(x) for x in re.split(r"(?<=[।!?])\s+", base.clean(narration)) if base.clean(x)]
    if parts and re.match(r"^\S+ राशि[।:]", parts[0]):
        parts = parts[1:]
    cues = []
    for p in parts:
        p = re.sub(r"^(आज का दिन कुल मिलाकर|आज)\s+", "", p).strip()
        if len(p) > 58:
            p = p[:55].rsplit(" ", 1)[0] + "…"
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


def _save(canvas, out):
    canvas.convert("RGB").save(out, "JPEG", quality=98, subsampling=0)
    return out


def _intro_background():
    canvas = Image.new("RGBA", (base.W, base.H), DARK)
    d = ImageDraw.Draw(canvas)
    cx, cy = base.W // 2, 610
    for r, alpha in ((500, 34), (440, 42), (380, 50)):
        d.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(247, 202, 77, alpha), width=3)
    d.ellipse((cx-455, cy-455, cx+455, cy+455), fill=(17, 5, 25, 205), outline=GOLD_SOFT, width=3)
    for x, y in ((105,355),(975,380),(135,820),(945,845),(90,1090),(990,1080),(230,1530),(850,1510)):
        d.ellipse((x-3,y-3,x+3,y+3), fill=GOLD_SOFT)
    return canvas


def premium_intro(script):
    out = base.SCENES / "000_intro.jpg"
    canvas = _intro_background()
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((20,20,base.W-20,base.H-20), radius=44, outline=GOLD, width=4)
    logo = _load_master_logo(900, 900)
    canvas.alpha_composite(logo, ((base.W-logo.width)//2, 610-logo.height//2))
    _center_text(d, "दैनिक वैदिक ज्योतिष", 1110, base.W-120, 62, CREAM, 40)
    date = next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")), "आज का दैनिक राशिफल")
    _panel(d, (55,1200,base.W-55,1285), 26)
    _center_text(d, date, 1222, base.W-140, 34, CREAM, 22)
    transition = next((x.strip() for x in script.splitlines() if "गोचर" in x or "प्रवेश" in x), "आज के प्रमुख ग्रह गोचर के संकेत")
    _panel(d, (55,1320,base.W-55,1545), 30)
    _center_text(d, "आज का प्रमुख गोचर", 1350, base.W-120, 34, GOLD, 24)
    y = 1402
    for line in base.wrap(transition, 44)[:2]:
        _center_text(d, line, y, base.W-130, 30, CREAM, 22)
        y += 48
    _center_text(d, "बारहों राशियों के लिए आज के ग्रह संकेत", 1615, base.W-100, 30, GOLD_SOFT, 20)
    return _save(canvas, out)


def _hero_with_anchor(canvas, source, box, anchor, radius=36):
    left, top, right, bottom = box
    width, height = right-left, bottom-top
    image = ImageOps.fit(ImageOps.exif_transpose(source.convert("RGB")), (width, height), method=Image.Resampling.LANCZOS, centering=anchor)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,width-1,height-1), radius=radius, fill=255)
    canvas.paste(image, (left,top), mask)


def premium_rashi(index, key, label, deity, image_path, narration):
    out = base.SCENES / f"{index:03d}_{key}.jpg"
    profile = RASHI_PROFILES[key]
    canvas = base.background()
    d = ImageDraw.Draw(canvas)
    _header(canvas)
    hero_box = (32, 300, base.W-32, 1045)
    with Image.open(image_path) as im:
        _hero_with_anchor(canvas, im, hero_box, profile["hero_anchor"], radius=36)
    d.rounded_rectangle(hero_box, radius=36, outline=GOLD, width=3)

    _panel(d, (40,1075,base.W-40,1168), 28)
    # Avoid Unicode bullets that can render as tofu on the CI font.
    title = f"{index:02d}   {label}"
    _center_text(d, title, 1096, base.W-140, 44, CREAM, 28)

    element = f"तत्व  —  {profile['element']}"
    planet = f"स्वामी  —  {profile['planet']}"
    chips = [(element, 65, 1192, 515), (planet, 565, 1192, 1015)]
    for text, left, top, right in chips:
        d.rounded_rectangle((left,top,right,1262), radius=24, fill=(52,18,49,245), outline=(247,202,77,150), width=2)
        f = base.fit(d, text, right-left-28, 25, 19)
        b = d.textbbox((0,0), text, font=f)
        d.text((left+(right-left-(b[2]-b[0]))/2,1212), text, font=f, fill=GOLD_SOFT)

    tone = _tone(narration)
    _panel(d, (40,1292,base.W-40,1740), 32)
    _center_text(d, "आज का संकेत", 1320, base.W-140, 34, GOLD, 24)
    _center_text(d, tone, 1368, base.W-140, 32, CREAM, 24)
    cues = _short_cues(narration)
    y = 1435
    cue_left = 125
    cue_right = base.W - 75
    for i, cue in enumerate(cues):
        d.ellipse((82,y+13,96,y+27), fill=GOLD)
        f = base.fit(d, cue, cue_right-cue_left, 31, 23)
        d.text((cue_left,y), cue, font=f, fill=CREAM)
        if i < 2:
            d.line((110,y+58,base.W-110,y+58), fill=(247,202,77,70), width=1)
        y += 88
    return _save(canvas, out)


def premium_outro():
    out = base.SCENES / "013_outro.jpg"
    canvas = Image.new("RGBA", (base.W, base.H), DARK)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((20,20,base.W-20,base.H-20), radius=44, outline=GOLD, width=4)
    _header(canvas)
    _center_text(d, "शुभम् भवतु", 620, base.W-150, 70, CREAM, 44)
    for y, line in zip((805,885,965), ["आपका दिन शुभ और मंगलमय हो", "ईश्वर की कृपा आपके साथ रहे", "कल फिर मिलेंगे नए ग्रह संकेतों के साथ"]):
        _center_text(d, line, y, base.W-180, 36, CREAM, 25)
    _center_text(d, "ॐ  •  आस्था  •  ज्योतिष  •  शुभ संकेत  •  ॐ", 1160, base.W-120, 28, GOLD_SOFT, 20)
    return _save(canvas, out)


def premium_motion(ffmpeg, scene, seconds, index):
    """Render restrained continuous motion from data-driven scene profiles."""
    out = base.SCENES / f"motion_{index:02d}.mp4"
    seconds = max(0.5, float(seconds))
    frames = max(2, int(round(seconds * base.FPS)))
    if index == 0 or index == len(base.RASHIS) + 1:
        profile = MOTION["intro"]
    else:
        key = base.RASHIS[index-1][0]
        profile = MOTION[RASHI_PROFILES[key]["motion"]]
    scale = profile["scale"]
    sw = int(base.W * scale) // 2 * 2
    sh = int(base.H * scale) // 2 * 2
    sx, sy = profile["start"]
    ex, ey = profile["end"]
    x = f"(in_w-out_w)*({sx:.4f}+({ex:.4f}-{sx:.4f})*n/{frames-1})"
    y = f"(in_h-out_h)*({sy:.4f}+({ey:.4f}-{sy:.4f})*n/{frames-1})"
    fade = min(0.30, max(0.12, seconds/8))
    fade_out = max(0.05, seconds-fade)
    vf = (f"scale={sw}:{sh}:force_original_aspect_ratio=disable,"
          f"crop={base.W}:{base.H}:x='{x}':y='{y}',fps={base.FPS},"
          f"fade=t=in:st=0:d={fade:.3f},fade=t=out:st={fade_out:.3f}:d={fade:.3f}")
    base.run([ffmpeg,"-y","-loop","1","-i",scene,"-vf",vf,"-t",f"{seconds:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p",out],900)
    return out


def main():
    _assert_brand_asset()
    if set(RASHI_PROFILES) != {x[0] for x in base.RASHIS}:
        raise RuntimeError("Rashi visual-profile coverage mismatch")
    base.intro = premium_intro
    base.rashi_scene = premium_rashi
    base.outro = premium_outro
    base.motion = premium_motion
    base.main()


if __name__ == "__main__":
    main()
