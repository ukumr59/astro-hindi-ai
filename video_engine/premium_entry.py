"""AstroPratidin premium production renderer.

Hard production rules:
- The ONLY AstroPratidin brand mark is the exact supplied file:
  assets/AstroPratidin Logo.png
- Never redraw, retype, approximate, or substitute the logo.
- Never render legacy branding or replacement footers.
- Never render English brand text with the Devanagari font.
- Audio timing remains owned by render_sync.py.

V20.1 visual direction:
- The intro uses the exact master logo as the dominant central focal point.
- The logo sits inside the existing concentric astrology rings, not in a tiny
  header, so the channel identity is immediately recognizable.
- The intro has no legacy artwork and no footer/footnote.
"""
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageOps
from . import render_sync as base

ROOT = Path(__file__).resolve().parents[1]
MASTER_LOGO = ROOT / "assets" / "AstroPratidin Logo.png"
GOLD = (247, 202, 77, 255)
GOLD_SOFT = (255, 226, 125, 230)
CREAM = (255, 244, 214, 255)
DARK = (25, 7, 34, 255)
PANEL = (31, 9, 38, 248)


def _assert_brand_asset():
    if not MASTER_LOGO.exists():
        raise RuntimeError(f"Missing exact AstroPratidin master logo: {MASTER_LOGO}")


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
    x = (base.W - logo.width) // 2
    y = 42 + (205 - logo.height) // 2
    canvas.alpha_composite(logo, (x, y))
    d.line((100, 250, base.W - 100, 250), fill=(247, 202, 77, 110), width=1)


def _panel(d, box, radius=30):
    d.rounded_rectangle(box, radius=radius, fill=PANEL, outline=GOLD, width=2)


def _short_cues(narration):
    text = base.clean(narration)
    parts = [base.clean(x) for x in re.split(r"(?<=[।!?])\s+", text) if base.clean(x)]
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
    for r, alpha in ((500, 24), (440, 30), (380, 38), (320, 48), (260, 58)):
        d.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(247, 202, 77, alpha), width=3)
    d.ellipse((cx-150, cy-150, cx+150, cy+150), fill=(48, 16, 50, 235), outline=GOLD, width=3)
    d.ellipse((cx-42, cy-42, cx+42, cy+42), fill=GOLD)
    for dx, dy in ((0,-220),(0,220),(-220,0),(220,0),(-155,-155),(155,-155),(-155,155),(155,155)):
        d.line((cx, cy, cx+dx, cy+dy), fill=GOLD_SOFT, width=3)
    for x, y in ((105,355),(975,380),(135,820),(945,845),(90,1090),(990,1080),(230,1530),(850,1510)):
        d.ellipse((x-3,y-3,x+3,y+3), fill=GOLD_SOFT)
    return canvas


def premium_intro(script):
    out = base.SCENES / "000_intro.jpg"
    canvas = _intro_background()
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((20,20,base.W-20,base.H-20), radius=44, outline=GOLD, width=4)

    # The exact supplied AstroPratidin master logo is the dominant focal point.
    # It is centered over the concentric astrology rings and is NOT repeated
    # in the small header used by the Rashi cards.
    logo = _load_master_logo(440, 440)
    logo_x = (base.W - logo.width) // 2
    logo_y = 610 - logo.height // 2
    # Subtle halo gives the real logo separation from the ring artwork.
    halo_r = max(logo.width, logo.height) // 2 + 18
    d.ellipse((base.W//2-halo_r, 610-halo_r, base.W//2+halo_r, 610+halo_r), fill=(17,5,25,190), outline=GOLD_SOFT, width=3)
    canvas.alpha_composite(logo, (logo_x, logo_y))

    title = "दैनिक वैदिक ज्योतिष"
    f = base.fit(d, title, base.W - 120, 62, 40)
    b = d.textbbox((0,0), title, font=f)
    d.text(((base.W-(b[2]-b[0]))/2, 940), title, font=f, fill=CREAM)

    date = next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")), "आज का दैनिक राशिफल")
    f = base.fit(d, date, base.W - 140, 34, 22)
    _panel(d, (55,1040,base.W-55,1130), 26)
    b = d.textbbox((0,0), date, font=f)
    d.text(((base.W-(b[2]-b[0]))/2,1063), date, font=f, fill=CREAM)

    transition = next((x.strip() for x in script.splitlines() if "गोचर" in x or "प्रवेश" in x), "आज के प्रमुख ग्रह गोचर के संकेत")
    _panel(d, (55,1170,base.W-55,1425), 30)
    f = base.fit(d, "आज का प्रमुख गोचर", base.W-120, 34, 24)
    b = d.textbbox((0,0), "आज का प्रमुख गोचर", font=f)
    d.text(((base.W-(b[2]-b[0]))/2,1200), "आज का प्रमुख गोचर", font=f, fill=GOLD)
    y = 1260
    for line in base.wrap(transition, 45)[:3]:
        f = base.fit(d, line, base.W-130, 30, 22)
        b = d.textbbox((0,0), line, font=f)
        d.text(((base.W-(b[2]-b[0]))/2,y), line, font=f, fill=CREAM)
        y += 48

    sub = "बारहों राशियों के लिए आज के ग्रह संकेत"
    f = base.fit(d, sub, base.W-100, 30, 22)
    b = d.textbbox((0,0), sub, font=f)
    d.text(((base.W-(b[2]-b[0]))/2,1515), sub, font=f, fill=GOLD_SOFT)
    return _save(canvas, out)


def premium_rashi(index, key, label, deity, image_path, narration):
    out = base.SCENES / f"{index:03d}_{key}.jpg"
    canvas = base.background()
    d = ImageDraw.Draw(canvas)
    _header(canvas)
    hero_top, hero_bottom = 300, 1040
    with Image.open(image_path) as im:
        deity_img = ImageOps.exif_transpose(im.convert("RGB"))
    base.put_hero(canvas, deity_img, (32, hero_top, base.W-32, hero_bottom), radius=36)
    d.rounded_rectangle((32,hero_top,base.W-32,hero_bottom), radius=36, outline=GOLD, width=3)
    _panel(d, (40,1070,base.W-40,1815), 34)
    badge = f"{index:02d}  {label}"
    f = base.fit(d, badge, base.W-140, 46, 30)
    b = d.textbbox((0,0), badge, font=f)
    d.text(((base.W-(b[2]-b[0]))/2,1105), badge, font=f, fill=CREAM)
    d.line((105,1170,base.W-105,1170), fill=(247,202,77,140), width=2)
    tone = _tone(narration)
    f = base.fit(d, tone, 330, 30, 22)
    b = d.textbbox((0,0), tone, font=f)
    pill_w = b[2]-b[0]+56
    px = (base.W-pill_w)/2
    d.rounded_rectangle((px,1200,px+pill_w,1270), radius=28, fill=(60,22,52,255), outline=GOLD, width=2)
    d.text((px+28,1218), tone, font=f, fill=GOLD)
    cues = _short_cues(narration)
    y = 1310
    for i, cue in enumerate(cues):
        d.ellipse((80,y+15,94,y+29), fill=GOLD)
        f = base.fit(d, cue, base.W-170, 32, 23)
        b = d.textbbox((0,0), cue, font=f)
        d.text(((base.W-(b[2]-b[0]))/2+8,y), cue, font=f, fill=CREAM)
        if i < 2:
            d.line((105,y+76,base.W-105,y+76), fill=(247,202,77,75), width=1)
        y += 112
    # Deliberately no footer, no footnote, no retyped English brand name.
    return _save(canvas, out)


def premium_outro():
    out = base.SCENES / "013_outro.jpg"
    canvas = Image.new("RGBA", (base.W, base.H), DARK)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((20,20,base.W-20,base.H-20), radius=44, outline=GOLD, width=4)
    _header(canvas)
    title = "शुभम् भवतु"
    f = base.fit(d, title, base.W-150, 70, 44)
    b = d.textbbox((0,0), title, font=f)
    d.text(((base.W-(b[2]-b[0]))/2,620), title, font=f, fill=CREAM)
    lines = ["आपका दिन शुभ और मंगलमय हो", "ईश्वर की कृपा आपके साथ रहे", "कल फिर मिलेंगे नए ग्रह संकेतों के साथ"]
    y = 800
    for line in lines:
        f = base.fit(d, line, base.W-180, 36, 25)
        b = d.textbbox((0,0), line, font=f)
        d.text(((base.W-(b[2]-b[0]))/2,y), line, font=f, fill=CREAM)
        y += 82
    return _save(canvas, out)


def premium_motion(ffmpeg, scene, seconds, index):
    out = base.SCENES / f"motion_{index:02d}.mp4"
    seconds = max(0.5, float(seconds))
    fade = min(0.28, max(0.12, seconds / 8))
    start = max(0.05, seconds - fade)
    sw = base.W * 108 // 100 // 2 * 2
    sh = base.H * 108 // 100 // 2 * 2
    vf = (f"scale={sw}:{sh}:force_original_aspect_ratio=disable,"
          f"crop={base.W}:{base.H}:x=(in_w-out_w)/2:y=(in_h-out_h)/2,"
          f"fps={base.FPS},fade=t=in:st=0:d={fade:.3f},fade=t=out:st={start:.3f}:d={fade:.3f}")
    base.run([ffmpeg,"-y","-loop","1","-i",scene,"-vf",vf,"-t",f"{seconds:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p",out],900)
    return out


def main():
    _assert_brand_asset()
    base.intro = premium_intro
    base.rashi_scene = premium_rashi
    base.outro = premium_outro
    base.motion = premium_motion
    base.main()


if __name__ == "__main__":
    main()
