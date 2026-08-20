"""AstroPratidin V21 premium renderer.

Final visual-polish architecture:
- Immutable exact AstroPratidin master logo.
- One consistent brand grid across intro, Rashi cards and outro.
- Data-driven Rashi art direction and motion.
- Audio remains the master timeline.
- No legacy footer/footnote or duplicate logo artwork.
- All text stays inside a shared safe rail.
- Display copy is complete and deliberately concise; no ellipsis truncation.
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

SAFE = 58
PANEL_LEFT = 48
PANEL_RIGHT = base.W - 48


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
        return src.resize(
            (max(1, int(src.width * ratio)), max(1, int(src.height * ratio))),
            Image.Resampling.LANCZOS,
        )


def _panel(d, box, radius=30, fill=PANEL):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=GOLD, width=2)


def _center_text(d, text, y, max_width, size, fill=CREAM, minimum=20):
    f = base.fit(d, text, max_width, size, minimum)
    b = d.textbbox((0, 0), text, font=f)
    d.text(((base.W - (b[2] - b[0])) / 2, y), text, font=f, fill=fill)
    return f


def _header(canvas):
    """Shared Rashi/outro header using the exact supplied master logo."""
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((28, 26, base.W - 28, 276), radius=34, fill=DARK, outline=GOLD, width=2)
    logo = _load_master_logo(280, 228)
    canvas.alpha_composite(logo, ((base.W - logo.width) // 2, 36 + (228 - logo.height) // 2))
    d.line((90, 252, base.W - 90, 252), fill=(247, 202, 77, 110), width=1)


def _split_sentences(narration):
    return [base.clean(x) for x in re.split(r"(?<=[।!?])\s+", base.clean(narration)) if base.clean(x)]


def _short_cues(narration):
    """Create three complete, production-ready display cues from the narration.

    The narration can contain long editorial sentences. The visual card deliberately
    uses concise complete statements so the design never clips or appends ellipses.
    """
    parts = _split_sentences(narration)
    if parts and re.match(r"^\S+ राशि[।:]", parts[0]):
        parts = parts[1:]
    status = parts[0] if parts else "आज संतुलित और सावधानी से आगे बढ़ें।"
    transit = parts[1] if len(parts) > 1 else "आज के ग्रह गोचर के संकेत ध्यान से समझें।"

    if "जल्दबाजी" in narration:
        action = "जल्दबाजी से बचें, खर्च नियंत्रित रखें और रिश्तों में संयम रखें।"
    elif "स्पष्ट संवाद" in narration:
        action = "काम, धन और रिश्तों में स्पष्ट संवाद तथा संतुलन रखें।"
    elif "अवसरों का लाभ" in narration:
        action = "काम में अवसरों का लाभ लें और धन संबंधी निर्णय सोच-समझकर करें।"
    else:
        action = "काम और धन संबंधी निर्णय सोच-समझकर लें।"

    # Keep the status concise without changing its meaning.
    status = re.sub(r"^आज का दिन कुल मिलाकर\s+", "आज ", status)
    return [status, transit, action]


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
    """Minimal brand-safe intro background; the master logo owns the circular geometry."""
    canvas = Image.new("RGBA", (base.W, base.H), DARK)
    d = ImageDraw.Draw(canvas)
    # Subtle star points only. No independent concentric rings that can conflict
    # with the exact circular geometry already present in the supplied logo.
    for x, y, r in ((72,330,3),(1004,360,3),(105,820,3),(975,850,3),(92,1085,3),(990,1090,3),(170,1510,2),(910,1510,2)):
        d.ellipse((x-r,y-r,x+r,y+r), fill=GOLD_SOFT)
    return canvas


def premium_intro(script):
    out = base.SCENES / "000_intro.jpg"
    canvas = _intro_background()
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((20,20,base.W-20,base.H-20), radius=44, outline=GOLD, width=4)

    # The approved master logo is the dominant circular visual element.
    logo = _load_master_logo(900, 900)
    canvas.alpha_composite(logo, ((base.W-logo.width)//2, 610-logo.height//2))

    # Keep the requested title lower, while maintaining a coherent vertical stack.
    _center_text(d, "दैनिक वैदिक ज्योतिष", 1138, base.W-140, 62, CREAM, 40)

    date = next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")), "आज का दैनिक राशिफल")
    _panel(d, (55,1220,base.W-55,1306), 26)
    _center_text(d, date, 1242, base.W-150, 34, CREAM, 22)

    # Prefer the actual transit event, not the heading "आज के प्रमुख ग्रह परिवर्तन".
    lines = [x.strip() for x in script.splitlines() if x.strip()]
    transition_candidates = [
        x for x in lines
        if ("प्रवेश" in x or "गोचर कर रहा है" in x) and "राशि" in x
    ]
    transition = transition_candidates[0] if transition_candidates else "आज के प्रमुख ग्रह गोचर के संकेत जानिए।"

    _panel(d, (55,1340,base.W-55,1595), 30)
    _center_text(d, "आज का प्रमुख गोचर", 1370, base.W-140, 34, GOLD, 24)
    y = 1424
    for line in base.wrap(transition, 46)[:3]:
        _center_text(d, line, y, base.W-150, 30, CREAM, 22)
        y += 48
    _center_text(d, "बारहों राशियों के लिए आज के ग्रह संकेत", 1660, base.W-140, 30, GOLD_SOFT, 20)
    return _save(canvas, out)


def _hero_with_anchor(canvas, source, box, anchor, radius=36):
    left, top, right, bottom = box
    width, height = right-left, bottom-top
    image = ImageOps.fit(ImageOps.exif_transpose(source.convert("RGB")), (width, height), method=Image.Resampling.LANCZOS, centering=anchor)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,width-1,height-1), radius=radius, fill=255)
    canvas.paste(image, (left,top), mask)


def _fit_wrapped_lines(d, text, max_width, max_lines=2, size=29, minimum=20):
    words = text.split()
    for n in range(size, minimum-1, -1):
        f = base.font(n)
        lines = []
        current = ""
        for word in words:
            candidate = word if not current else current + " " + word
            b = d.textbbox((0,0), candidate, font=f)
            if b[2]-b[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if len(lines) <= max_lines:
            return f, lines
    f = base.font(minimum)
    return f, [text]


def _draw_cue(d, cue, y):
    f, lines = _fit_wrapped_lines(d, cue, base.W-205, max_lines=2, size=29, minimum=20)
    line_height = max(34, int(f.size * 1.35))
    d.ellipse((78,y+10,94,y+26), fill=GOLD)
    line_y = y
    for line in lines:
        d.text((118,line_y), line, font=f, fill=CREAM)
        line_y += line_height
    return max(84, len(lines)*line_height + 24)


def premium_rashi(index, key, label, deity, image_path, narration):
    out = base.SCENES / f"{index:03d}_{key}.jpg"
    profile = RASHI_PROFILES[key]
    canvas = base.background()
    d = ImageDraw.Draw(canvas)
    _header(canvas)
    hero_box = (32,300,base.W-32,1045)
    with Image.open(image_path) as im:
        _hero_with_anchor(canvas, im, hero_box, profile["hero_anchor"], radius=36)
    d.rounded_rectangle(hero_box, radius=36, outline=GOLD, width=3)

    _panel(d, (48,1075,base.W-48,1168), 28)
    _center_text(d, f"{index:02d}   {label}", 1096, base.W-140, 44, CREAM, 28)

    element = f"तत्व  —  {profile['element']}"
    planet = f"स्वामी  —  {profile['planet']}"
    for text, left, top, right in [(element,62,1192,520),(planet,560,1192,1018)]:
        d.rounded_rectangle((left,top,right,1262), radius=24, fill=(52,18,49,245), outline=(247,202,77,150), width=2)
        f = base.fit(d, text, right-left-28, 25, 19)
        b = d.textbbox((0,0), text, font=f)
        d.text((left+(right-left-(b[2]-b[0]))/2,1212), text, font=f, fill=GOLD_SOFT)

    _panel(d, (48,1292,base.W-48,1810), 32)
    _center_text(d, "आज का संकेत", 1320, base.W-140, 34, GOLD, 24)
    _center_text(d, _tone(narration), 1368, base.W-140, 32, CREAM, 24)
    y = 1432
    cues = _short_cues(narration)
    for i, cue in enumerate(cues):
        used = _draw_cue(d, cue, y)
        if i < 2:
            d.line((110,y+used-12,base.W-110,y+used-12), fill=(247,202,77,70), width=1)
        y += used
    return _save(canvas, out)


def premium_outro():
    out = base.SCENES / "013_outro.jpg"
    canvas = Image.new("RGBA", (base.W,base.H), DARK)
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
    sw = int(base.W*scale)//2*2
    sh = int(base.H*scale)//2*2
    sx, sy = profile["start"]
    ex, ey = profile["end"]
    x = f"(in_w-out_w)*({sx:.4f}+({ex:.4f}-{sx:.4f})*n/{frames-1})"
    y = f"(in_h-out_h)*({sy:.4f}+({ey:.4f}-{sy:.4f})*n/{frames-1})"
    fade = min(0.30,max(0.12,seconds/8))
    fade_out = max(0.05,seconds-fade)
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
