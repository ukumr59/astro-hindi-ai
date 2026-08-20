"""AstroPratidin V21 premium renderer.

V21.6 visual polish:
- The supplied master logo is the only circular brand geometry; decorative
  background rings are intentionally removed so concentric circles cannot
  drift out of registration with the logo artwork.
- Intro typography is lowered as one coherent stack.
- All rashi text panels use a conservative inner safe margin so borders never
  visually touch the video edge.
- Rashi identity and insight rows share fixed alignment rails across all 12
  signs.
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

# Deliberately generous vertical-video safe area. Keeping all text panels
# inside this rail prevents edge clipping after player/browser scaling.
SAFE_X = 72
SAFE_RIGHT = base.W - SAFE_X


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
    d.rounded_rectangle((SAFE_X, 26, SAFE_RIGHT, 276), radius=34, fill=DARK, outline=GOLD, width=2)
    logo = _load_master_logo(230, 205)
    canvas.alpha_composite(logo, ((base.W-logo.width)//2, 42 + (205-logo.height)//2))
    d.line((SAFE_X + 70, 250, SAFE_RIGHT - 70, 250), fill=(247, 202, 77, 110), width=1)


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
    # The master AstroPratidin logo already contains its own concentric gold
    # rings. Do not draw a second set behind it: even a small centre/scale
    # difference makes the circles appear misregistered in the final video.
    canvas = Image.new("RGBA", (base.W, base.H), DARK)
    d = ImageDraw.Draw(canvas)
    for x, y in ((105,355),(975,380),(135,820),(945,845),(90,1090),(990,1080),(230,1530),(850,1510)):
        d.ellipse((x-3,y-3,x+3,y+3), fill=GOLD_SOFT)
    return canvas


def premium_intro(script):
    out = base.SCENES / "000_intro.jpg"
    canvas = _intro_background()
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((SAFE_X,20,SAFE_RIGHT,base.H-20), radius=44, outline=GOLD, width=4)

    # Exact master logo: keep its own circular geometry intact.
    logo = _load_master_logo(900, 900)
    canvas.alpha_composite(logo, ((base.W-logo.width)//2, 610-logo.height//2))

    # Lower the complete typography stack together. This preserves hierarchy
    # while giving the logo visual breathing room and avoiding the previous
    # title/date/gochar crowding.
    _center_text(d, "दैनिक वैदिक ज्योतिष", 1160, base.W-180, 62, CREAM, 40)
    date = next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")), "आज का दैनिक राशिफल")
    _panel(d, (SAFE_X,1250,SAFE_RIGHT,1335), 26)
    _center_text(d, date, 1273, base.W-210, 34, CREAM, 22)

    transition = next((x.strip() for x in script.splitlines() if "गोचर" in x or "प्रवेश" in x), "आज के प्रमुख ग्रह गोचर के संकेत")
    _panel(d, (SAFE_X,1370,SAFE_RIGHT,1600), 30)
    _center_text(d, "आज का प्रमुख गोचर", 1400, base.W-200, 34, GOLD, 24)
    y = 1452
    for line in base.wrap(transition, 44)[:2]:
        _center_text(d, line, y, base.W-220, 30, CREAM, 22)
        y += 48
    _center_text(d, "बारहों राशियों के लिए आज के ग्रह संकेत", 1670, base.W-180, 30, GOLD_SOFT, 20)
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

    hero_box = (SAFE_X, 300, SAFE_RIGHT, 1045)
    with Image.open(image_path) as im:
        _hero_with_anchor(canvas, im, hero_box, profile["hero_anchor"], radius=36)
    d.rounded_rectangle(hero_box, radius=36, outline=GOLD, width=3)

    _panel(d, (SAFE_X,1075,SAFE_RIGHT,1168), 28)
    title = f"{index:02d}   {label}"
    _center_text(d, title, 1096, base.W-220, 44, CREAM, 28)

    element = f"तत्व  —  {profile['element']}"
    planet = f"स्वामी  —  {profile['planet']}"
    chip_gap = 28
    chip_w = (SAFE_RIGHT - SAFE_X - chip_gap) // 2
    chips = [
        (element, SAFE_X, 1192, SAFE_X + chip_w),
        (planet, SAFE_X + chip_w + chip_gap, 1192, SAFE_RIGHT),
    ]
    for text, left, top, right in chips:
        d.rounded_rectangle((left,top,right,1262), radius=24, fill=(52,18,49,245), outline=(247,202,77,150), width=2)
        f = base.fit(d, text, right-left-28, 25, 19)
        b = d.textbbox((0,0), text, font=f)
        d.text((left+(right-left-(b[2]-b[0]))/2,1212), text, font=f, fill=GOLD_SOFT)

    tone = _tone(narration)
    _panel(d, (SAFE_X,1292,SAFE_RIGHT,1740), 32)
    _center_text(d, "आज का संकेत", 1320, base.W-220, 34, GOLD, 24)
    _center_text(d, tone, 1368, base.W-220, 32, CREAM, 24)
    cues = _short_cues(narration)
    y = 1435
    cue_left = SAFE_X + 52
    cue_right = SAFE_RIGHT - 32
    for i, cue in enumerate(cues):
        d.ellipse((SAFE_X+18,y+13,SAFE_X+32,y+27), fill=GOLD)
        f = base.fit(d, cue, cue_right-cue_left, 31, 23)
        d.text((cue_left,y), cue, font=f, fill=CREAM)
        if i < 2:
            d.line((SAFE_X+42,y+58,SAFE_RIGHT-42,y+58), fill=(247,202,77,70), width=1)
        y += 88
    return _save(canvas, out)


def premium_outro():
    out = base.SCENES / "013_outro.jpg"
    canvas = Image.new("RGBA", (base.W, base.H), DARK)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((SAFE_X,20,SAFE_RIGHT,base.H-20), radius=44, outline=GOLD, width=4)
    _header(canvas)
    _center_text(d, "शुभम् भवतु", 620, base.W-220, 70, CREAM, 44)
    for y, line in zip((805,885,965), ["आपका दिन शुभ और मंगलमय हो", "ईश्वर की कृपा आपके साथ रहे", "कल फिर मिलेंगे नए ग्रह संकेतों के साथ"]):
        _center_text(d, line, y, base.W-240, 36, CREAM, 25)
    _center_text(d, "ॐ  •  आस्था  •  ज्योतिष  •  शुभ संकेत  •  ॐ", 1160, base.W-220, 28, GOLD_SOFT, 20)
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
