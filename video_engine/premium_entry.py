"""Premium AstroPratidin presentation layer.

Keeps the existing audio-led renderer as the source of truth for narration,
scene order and timing, while replacing only presentation functions:
- circular AstroPratidin brand mark
- concise on-screen cues instead of repeating full narration
- cleaner intro hierarchy
- cinematic time-based drift/zoom without zoompan
- stronger visual depth and particles
"""
from pathlib import Path
import re
import subprocess

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from . import render_sync as base

BRAND = "AstroPratidin"
TAGLINE = "दैनिक वैदिक ज्योतिष"
GOLD = (247, 202, 77, 255)
CREAM = (255, 244, 214, 255)
DARK = (28, 5, 31, 238)


def _logo(canvas, x=42, y=52, size=118):
    layer = Image.new("RGBA", (size + 8, size + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((4, 4, size + 4, size + 4), fill=(20, 5, 28, 235), outline=GOLD, width=4)
    d.ellipse((11, 11, size - 3, size - 3), outline=(255, 226, 125, 180), width=2)
    om = "ॐ"
    of = base.font(max(30, int(size * .30)))
    b = d.textbbox((0, 0), om, font=of)
    d.text(((size + 8 - (b[2]-b[0]))/2, 8), om, font=of, fill=GOLD)
    bf = base.fit(d, BRAND, size - 16, max(15, int(size * .15)), 12)
    b = d.textbbox((0, 0), BRAND, font=bf)
    d.text(((size + 8 - (b[2]-b[0]))/2, size*.48), BRAND, font=bf, fill=CREAM)
    tf = base.fit(d, TAGLINE, size - 12, max(10, int(size * .095)), 9)
    b = d.textbbox((0, 0), TAGLINE, font=tf)
    d.text(((size + 8 - (b[2]-b[0]))/2, size*.73), TAGLINE, font=tf, fill=GOLD)
    canvas.alpha_composite(layer, (x, y))


def _particles(canvas, seed, count=30):
    import random
    rng = random.Random(seed)
    d = ImageDraw.Draw(canvas)
    for _ in range(count):
        x = rng.randint(35, base.W - 35)
        y = rng.randint(35, base.H - 35)
        r = rng.choice((1, 1, 1, 2))
        d.ellipse((x-r, y-r, x+r, y+r), fill=(247, 202, 77, rng.randint(45, 120)))


def _short_cues(narration):
    text = base.clean(narration)
    parts = [base.clean(x) for x in re.split(r"(?<=[।!?])\s+", text) if base.clean(x)]
    if parts and re.match(r"^\S+ राशि[।:]", parts[0]):
        parts = parts[1:]
    cues = []
    for p in parts:
        p = re.sub(r"^(आज का दिन कुल मिलाकर|आज)\s+", "", p).strip()
        if len(p) > 52:
            p = p[:49].rsplit(" ", 1)[0] + "…"
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
    hero = base.crop_cover(source, base.W - 64, 1015)
    canvas.alpha_composite(hero.convert("RGBA"), (32, 50))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((20, 20, base.W-20, base.H-20), radius=46, outline=GOLD, width=4)
    d.rounded_rectangle((32, 50, base.W-32, 1070), radius=36, outline=(247,202,77,190), width=2)
    _logo(canvas, 48, 70, 125)
    _particles(canvas, 101, 45)

    title = "॥ दैनिक वैदिक ज्योतिष ॥"
    f = base.fit(d, title, base.W-120, 62, 40)
    b = d.textbbox((0,0), title, font=f)
    d.text(((base.W-(b[2]-b[0]))/2, 1110), title, font=f, fill=CREAM)

    date = next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")), "आज का दैनिक राशिफल")
    f = base.fit(d, date, base.W-140, 35, 23)
    d.rounded_rectangle((55,1188,base.W-55,1275), radius=28, fill=DARK, outline=GOLD, width=2)
    b=d.textbbox((0,0),date,font=f)
    d.text(((base.W-(b[2]-b[0]))/2,1210),date,font=f,fill=CREAM)

    transition = next((x.strip() for x in script.splitlines() if "गोचर" in x or "प्रवेश" in x), "आज के प्रमुख ग्रह गोचर के संकेत")
    d.rounded_rectangle((55,1300,base.W-55,1488), radius=30, fill=DARK, outline=GOLD, width=2)
    hf=base.fit(d,"आज का प्रमुख गोचर",base.W-120,31,23)
    b=d.textbbox((0,0),"आज का प्रमुख गोचर",font=hf)
    d.text(((base.W-(b[2]-b[0]))/2,1322),"आज का प्रमुख गोचर",font=hf,fill=GOLD)
    y=1370
    for line in base.wrap(transition,48)[:2]:
        lf=base.fit(d,line,base.W-130,28,20)
        b=d.textbbox((0,0),line,font=lf)
        d.text(((base.W-(b[2]-b[0]))/2,y),line,font=lf,fill=CREAM)
        y+=46

    hook="ॐ  •  आस्था  •  ग्रह गोचर  •  शुभ संकेत  •  ॐ"
    hf=base.fit(d,hook,base.W-100,29,19); b=d.textbbox((0,0),hook,font=hf)
    d.text(((base.W-(b[2]-b[0]))/2,1565),hook,font=hf,fill=GOLD)
    sub="बारहों राशियों के लिए आज के ग्रह संकेत"
    sf=base.fit(d,sub,base.W-100,27,19); b=d.textbbox((0,0),sub,font=sf)
    d.text(((base.W-(b[2]-b[0]))/2,1660),sub,font=sf,fill=CREAM)
    canvas.convert("RGB").save(out,"JPEG",quality=98,subsampling=0)
    return out


def premium_rashi(index,key,label,deity,image_path,narration):
    out=base.SCENES/f"{index:03d}_{key}.jpg"
    canvas=base.background(); d=ImageDraw.Draw(canvas)
    base.put_hero(canvas, ImageOps.exif_transpose(Image.open(image_path).convert("RGB")), (32,52,base.W-32,1050), radius=36)
    d.rounded_rectangle((32,52,base.W-32,1050),radius=36,outline=GOLD,width=3)
    _logo(canvas,46,68,112); _particles(canvas,index*37,28)

    badge=f"{index:02d}  •  {label}"
    bf=base.fit(d,badge,base.W-130,44,28); b=d.textbbox((0,0),badge,font=bf)
    d.rounded_rectangle((48,1080,base.W-48,1170),radius=28,fill=DARK,outline=GOLD,width=2)
    d.text(((base.W-(b[2]-b[0]))/2,1103),badge,font=bf,fill=CREAM)

    tone=_tone(narration)
    tf=base.fit(d,tone,300,25,19); b=d.textbbox((0,0),tone,font=tf)
    d.rounded_rectangle((base.W-350,1195,base.W-45,1255),radius=23,fill=(55,21,52,245),outline=GOLD,width=2)
    d.text((base.W-197-(b[2]-b[0])/2,1208),tone,font=tf,fill=GOLD)

    cues=_short_cues(narration)
    y=1280
    for cue in cues:
        d.rounded_rectangle((55,y,base.W-55,y+105),radius=27,fill=(29,8,34,240),outline=(247,202,77,160),width=2)
        bf=base.font(27); d.text((86,y+35),"✦",font=bf,fill=GOLD)
        pf=base.fit(d,cue,base.W-190,30,21); b=d.textbbox((0,0),cue,font=pf)
        d.text(((base.W-(b[2]-b[0]))/2+18,y+32),cue,font=pf,fill=CREAM)
        y+=120
    prompt="विस्तृत फलादेश आवाज़ में • ध्यान से सुनें"
    pf=base.fit(d,prompt,base.W-100,24,18); b=d.textbbox((0,0),prompt,font=pf)
    d.text(((base.W-(b[2]-b[0]))/2,1685),prompt,font=pf,fill=(255,226,145,230))
    canvas.convert("RGB").save(out,"JPEG",quality=98,subsampling=0)
    return out


def premium_motion(ffmpeg,scene,seconds,index):
    out=base.SCENES/f"motion_{index:02d}.mp4"
    seconds=max(.5,float(seconds)); fade=min(.32,max(.12,seconds/7)); start=max(.05,seconds-fade)
    sw=base.W*112//100//2*2; sh=base.H*112//100//2*2
    period=max(4.0,seconds*1.25)
    x=f"(iw-ow)*(0.5+0.10*sin(2*PI*t/{period:.3f}))"
    y=f"(ih-oh)*(0.5+0.07*cos(2*PI*t/{period:.3f}))"
    vf=(f"scale={sw}:{sh}:force_original_aspect_ratio=disable,"
        f"crop={base.W}:{base.H}:x='{x}':y='{y}',fps={base.FPS},"
        f"fade=t=in:st=0:d={fade:.3f},fade=t=out:st={start:.3f}:d={fade:.3f}")
    base.run([ffmpeg,"-y","-loop","1","-i",scene,"-vf",vf,"-t",f"{seconds:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p",out],900)
    return out


def main():
    base.intro=premium_intro
    base.rashi_scene=premium_rashi
    base.motion=premium_motion
    base.main()


if __name__=="__main__":
    main()
