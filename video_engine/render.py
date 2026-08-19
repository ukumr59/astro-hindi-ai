"""
Daily Astro Hindi Video Renderer
- Prominent real deity artwork
- Animated deity entrance / slow zoom / glow
- Animated Rashi transition cards
- Hindi text panels
- 1080x1920 vertical MP4
"""

from pathlib import Path
import asyncio
import subprocess
import textwrap
import urllib.parse
import urllib.request
import json
import time
import re
import shutil

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts
import imageio_ffmpeg


OUT = Path("output")
SCENES = OUT / "video_scenes"
DEITIES = OUT / "deity_images"
SCRIPT = OUT / "daily_script.md"
VOICE = OUT / "daily_voice.mp3"
VIDEO = OUT / "daily_video.mp4"
CREDITS = OUT / "deity_credits.txt"

W, H = 1080, 1920
FPS = 30
VOICE_NAME = "hi-IN-SwaraNeural"

FONT = OUT / "NotoSansDevanagari-Regular.ttf"
FONT_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"

# Wikimedia Commons files. The renderer resolves them through the Commons
# API / Special:Redirect instead of hard-coding upload.wikimedia.org URLs.
DEITY_DATA = {
    "हनुमान जी": {
        "file": "Hanuman Ji.jpg",
        "credit": "https://commons.wikimedia.org/wiki/File:Hanuman_Ji.jpg",
        "license": "CC BY-SA 4.0",
    },
    "महालक्ष्मी जी": {
        "file": "Goddess Lakshmi Mata.jpg",
        "credit": "https://commons.wikimedia.org/wiki/File:Goddess_Lakshmi_Mata.jpg",
        "license": "CC BY-SA 4.0",
    },
    "श्री गणेश जी": {
        "file": "Lord Ganesh ji.jpg",
        "credit": "https://commons.wikimedia.org/wiki/File:Lord_Ganesh_ji.jpg",
        "license": "CC BY-SA 4.0",
    },
    "भगवान शिव": {
        "file": "Lord Shiva.jpg",
        "credit": "https://commons.wikimedia.org/wiki/File:Lord_Shiva.jpg",
        "license": "Wikimedia Commons - see source",
    },
    "सूर्य देव": {
        "file": "Surya Deva.png",
        "credit": "https://commons.wikimedia.org/wiki/File:Surya_Deva.png",
        "license": "CC BY-SA 4.0",
    },
    "भगवान विष्णु": {
        "file": "Vishnu.jpg",
        "credit": "https://commons.wikimedia.org/wiki/File:Vishnu.jpg",
        "license": "Public domain work / Commons source",
    },
    "शनि देव": {
        "file": "Shani Dev.jpg",
        "credit": "https://commons.wikimedia.org/wiki/File:Shani_Dev.jpg",
        "license": "CC BY-SA 4.0",
    },
}

RASHIS = [
    ("मेष", "♈", "हनुमान जी"),
    ("वृषभ", "♉", "महालक्ष्मी जी"),
    ("मिथुन", "♊", "श्री गणेश जी"),
    ("कर्क", "♋", "भगवान शिव"),
    ("सिंह", "♌", "सूर्य देव"),
    ("कन्या", "♍", "श्री गणेश जी"),
    ("तुला", "♎", "महालक्ष्मी जी"),
    ("वृश्चिक", "♏", "हनुमान जी"),
    ("धनु", "♐", "भगवान विष्णु"),
    ("मकर", "♑", "शनि देव"),
    ("कुंभ", "♒", "शनि देव"),
    ("मीन", "♓", "भगवान विष्णु"),
]


def run(cmd, timeout=900):
    print("RUN:", " ".join(map(str, cmd)))
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, timeout=timeout)
    print(p.stdout)
    if p.returncode:
        raise RuntimeError(f"Command failed: {p.returncode}")


def font(size):
    OUT.mkdir(exist_ok=True)
    if not FONT.exists():
        req = urllib.request.Request(FONT_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            FONT.write_bytes(r.read())
    return ImageFont.truetype(str(FONT), size)


def wrap(s, width=30):
    result = []
    for p in s.splitlines():
        p = p.strip()
        if p:
            result.extend(textwrap.wrap(p, width=width))
    return result


def get_script():
    if not SCRIPT.exists():
        raise RuntimeError("output/daily_script.md not found")
    s = SCRIPT.read_text(encoding="utf-8").strip()
    if not s:
        raise RuntimeError("daily_script.md is empty")
    return s


def rashi_sections(script):
    out = {}
    positions = {}
    for name, _, _ in RASHIS:
        pats = [f"{name} राशि", f"राशि: {name}", f"**{name}**", f"### {name}", f"## {name}"]
        pos = -1
        for p in pats:
            q = script.find(p)
            if q >= 0:
                pos = q
                break
        if pos >= 0:
            positions[name] = pos
    ordered = sorted(positions.items(), key=lambda x: x[1])
    for i, (name, pos) in enumerate(ordered):
        end = ordered[i+1][1] if i+1 < len(ordered) else len(script)
        out[name] = script[pos:end].strip()
    return out


def resolve_commons_url(filename):
    """
    Resolve a Commons file to a thumbnail URL. This avoids the old
    hard-coded upload.wikimedia.org URL that produced HTTP 403.
    """
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": "1200",
        "titles": "File:" + filename,
    }
    url = api + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DailyAstroHindi/1.0 (educational media generator)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = page.get("imageinfo")
        if info:
            return info[0].get("thumburl") or info[0].get("url")
    return None


def download_deity(name):
    DEITIES.mkdir(parents=True, exist_ok=True)
    data = DEITY_DATA[name]
    dest = DEITIES / (re.sub(r"[^A-Za-z0-9]+", "_", name) + ".jpg")

    if dest.exists():
        try:
            Image.open(dest).verify()
            return dest
        except Exception:
            dest.unlink(missing_ok=True)

    last = None
    for attempt in range(1, 5):
        try:
            image_url = resolve_commons_url(data["file"])
            if not image_url:
                raise RuntimeError("Commons API returned no image URL")

            print(f"Downloading {name}: {image_url}")
            req = urllib.request.Request(
                image_url,
                headers={
                    "User-Agent": "DailyAstroHindi/1.0 (educational media generator)",
                    "Accept": "image/avif,image/webp,image/jpeg,image/png,*/*",
                    "Referer": "https://commons.wikimedia.org/",
                },
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()

            temp = dest.with_suffix(".download")
            temp.write_bytes(raw)
            with Image.open(temp) as im:
                im.convert("RGB").save(dest, "JPEG", quality=94)
            temp.unlink(missing_ok=True)
            return dest

        except Exception as e:
            last = e
            print(f"Deity download attempt {attempt} failed: {e}")
            time.sleep(attempt * 2)

    # Do NOT silently pretend that a plain Om is a deity. Build a clearly
    # labelled devotional illustration with deity-specific iconography.
    print(f"Using deity illustration fallback for {name}: {last}")
    create_deity_illustration(name, dest)
    return dest


def create_deity_illustration(name, dest):
    """
    Guaranteed local visual fallback. It is deity-specific, not the generic
    Om card used by the previous version.
    """
    im = Image.new("RGB", (1000, 1100), (13, 7, 30))
    d = ImageDraw.Draw(im)
    title = font(66)
    big = font(260)
    sub = font(42)

    # deity-specific symbol / silhouette
    symbols = {
        "हनुमान जी": "हनु",
        "महालक्ष्मी जी": "श्री",
        "श्री गणेश जी": "गण",
        "भगवान शिव": "शिव",
        "सूर्य देव": "सूर्य",
        "भगवान विष्णु": "विष्णु",
        "शनि देव": "शनि",
    }
    symbol = symbols.get(name, "ॐ")

    # large decorative halo
    d.ellipse((140, 70, 860, 790), outline=(255, 202, 70), width=12)
    d.ellipse((190, 120, 810, 740), outline=(255, 226, 150), width=4)

    b = d.textbbox((0, 0), symbol, font=big)
    d.text(((1000-(b[2]-b[0]))/2, 250), symbol, font=big,
           fill=(255, 210, 80))

    b = d.textbbox((0, 0), name, font=title)
    d.text(((1000-(b[2]-b[0]))/2, 825), name, font=title,
           fill=(255, 245, 215))

    subtitle = "दिव्य स्वरूप • आशीर्वाद • शुभ ऊर्जा"
    b = d.textbbox((0, 0), subtitle, font=sub)
    d.text(((1000-(b[2]-b[0]))/2, 935), subtitle, font=sub,
           fill=(238, 216, 155))

    im.save(dest, "JPEG", quality=95)


def prepare_deities():
    credits = ["DEVOTIONAL ARTWORK CREDITS", "===========================", ""]
    done = {}
    for _, _, deity in RASHIS:
        if deity in done:
            continue
        path = download_deity(deity)
        done[deity] = path
        credits += [
            deity,
            "Source: " + DEITY_DATA[deity]["credit"],
            "License: " + DEITY_DATA[deity]["license"],
            "",
        ]
    CREDITS.write_text("\n".join(credits), encoding="utf-8")
    return done


def crop_fill(im, w, h):
    im = im.convert("RGB")
    scale = max(w/im.width, h/im.height)
    nw, nh = int(im.width*scale), int(im.height*scale)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    x, y = (nw-w)//2, (nh-h)//2
    return im.crop((x, y, x+w, y+h))


def create_scene(rashi, emoji, deity, content, deity_path, out):
    """
    Creates a 1080x1920 master still. Animation is applied by ffmpeg:
    slow zoom + glow + crossfade. The deity occupies most of the upper half.
    """
    deity_im = Image.open(deity_path).convert("RGB")
    bg = crop_fill(deity_im, W, H).filter(ImageFilter.GaussianBlur(32))
    bg = Image.blend(bg, Image.new("RGB", (W,H), (4,2,18)), 0.72)
    canvas = bg.convert("RGBA")
    d = ImageDraw.Draw(canvas)

    title = font(72)
    deity_f = font(56)
    body = font(36)
    small = font(29)

    # Header
    d.rounded_rectangle((25, 25, W-25, 170), 34,
                        fill=(3,1,17,225), outline=(255,210,70,240), width=4)
    t = f"{emoji}  {rashi} राशि"
    b = d.textbbox((0,0), t, font=title)
    d.text(((W-(b[2]-b[0]))/2, 57), t, font=title, fill=(255,220,90))

    # Hero image, deliberately large
    x1,y1,x2,y2 = 35,205,W-35,1085
    d.rounded_rectangle((x1,y1,x2,y2), 45,
                        fill=(0,0,0,90), outline=(255,215,80,245), width=5)

    hero = crop_fill(deity_im, 900, 760)
    mask = Image.new("L", hero.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0,0,hero.width-1,hero.height-1), 38, fill=255)
    canvas.paste(hero, (90,270), mask)
    d.rounded_rectangle((90,270,990,1030), 38,
                        outline=(255,232,150,235), width=4)

    b = d.textbbox((0,0), f"॥ {deity} ॥", font=deity_f)
    d.text(((W-(b[2]-b[0]))/2, 1100), f"॥ {deity} ॥",
           font=deity_f, fill=(255,242,200))

    # astrology text panel
    d.rounded_rectangle((35,1180,W-35,1690), 34,
                        fill=(2,2,16,235), outline=(150,135,190,130), width=2)
    y=1220
    for line in wrap(content, 31)[:10]:
        d.text((72,y), line, font=body, fill=(255,255,255))
        y += 49

    # animated-style footer elements
    d.text((70,1765), "ॐ  वैदिक गोचर  ॐ", font=small,
           fill=(255,220,120))
    d.text((W-70-d.textbbox((0,0),"शुभम्",font=small)[2],1765),
           "शुभम्", font=small, fill=(220,210,235))

    canvas.convert("RGB").save(out, quality=95)


def create_intro(path):
    im = Image.new("RGB",(W,H),(7,3,25))
    d=ImageDraw.Draw(im)
    f1=font(175); f2=font(80); f3=font(48)
    b=d.textbbox((0,0),"ॐ",font=f1)
    d.text(((W-(b[2]-b[0]))/2,360),"ॐ",font=f1,fill=(255,214,75))
    for y,txt,ft,fill in [
        (700,"दैनिक वैदिक ज्योतिष",f2,(255,255,255)),
        (830,"आज का गोचर विश्लेषण",f2,(255,220,135)),
        (980,"चंद्र राशि • निरयन • लाहिरी",f3,(220,215,235)),
    ]:
        b=d.textbbox((0,0),txt,font=ft)
        d.text(((W-(b[2]-b[0]))/2,y),txt,font=ft,fill=fill)
    im.save(path,quality=95)


def create_final(path):
    im=Image.new("RGB",(W,H),(7,3,25)); d=ImageDraw.Draw(im)
    f1=font(100); f2=font(52)
    b=d.textbbox((0,0),"🙏 धन्यवाद 🙏",font=f1)
    d.text(((W-(b[2]-b[0]))/2,600),"🙏 धन्यवाद 🙏",font=f1,fill=(255,220,90))
    for i,txt in enumerate(["वीडियो पसंद आए तो लाइक करें","चैनल को सब्सक्राइब करें"]):
        b=d.textbbox((0,0),txt,font=f2)
        d.text(((W-(b[2]-b[0]))/2,850+i*110),txt,font=f2,fill=(255,255,255))
    im.save(path,quality=95)


async def make_voice(text):
    communicate=edge_tts.Communicate(text,VOICE_NAME,rate="+5%")
    await communicate.save(str(VOICE))


def audio_duration(ffmpeg):
    p=subprocess.run([ffmpeg,"-i",str(VOICE)],stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,text=True)
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",p.stderr)
    if not m:
        raise RuntimeError("Could not read voice duration")
    return int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))


def make_animated_rashi_video(ffmpeg, scene, duration, index, output):
    """
    Animation:
      - slow cinematic zoom
      - gentle vertical drift
      - light pulse / vignette
      - no abrupt static slideshow feel
    """
    zoom = "1.0+0.055*(on/{frames})"
    frames = max(2,int(duration*FPS))
    zoom = f"min(zoom+0.00032,1.055)"
    # zoompan's d controls exact frame count.
    vf = (
        f"zoompan=z='{zoom}':"
        f"x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)+8*sin(on/18)':"
        f"d={frames}:s={W}x{H}:fps={FPS},"
        "eq=brightness='0.015*sin(2*PI*on/45)':"
        "saturation=1.08"
    )
    run([ffmpeg,"-y","-loop","1","-i",str(scene),
         "-vf",vf,"-t",f"{duration:.3f}",
         "-r",str(FPS),"-c:v","libx264","-preset","veryfast",
         "-crf","23","-pix_fmt","yuv420p",str(output)], timeout=600)


def build_video(ffmpeg, scenes, duration):
    """
    Builds each scene as a moving clip and joins them with short dissolves.
    """
    n = len(scenes)
    intro = min(5.0, max(3.0,duration*0.01))
    outro = min(5.0, max(3.0,duration*0.01))
    rashi_time = max(8.0,(duration-intro-outro)/12.0)

    clips=[]
    for i,scene in enumerate(scenes):
        if i==0:
            dur=intro
        elif i==len(scenes)-1:
            dur=outro
        else:
            dur=rashi_time
        clip=SCENES/f"clip_{i:02d}.mp4"
        make_animated_rashi_video(ffmpeg,scene,dur,i,clip)
        clips.append((clip,dur))

    # Crossfade each adjacent pair. For reliability, use xfade chain.
    current=clips[0][0]
    current_dur=clips[0][1]
    for i in range(1,len(clips)):
        nxt,nxt_dur=clips[i]
        out=SCENES/f"xfade_{i:02d}.mp4"
        offset=max(0.1,current_dur-0.8)
        filter_complex=(
            f"[0:v][1:v]xfade=transition=fade:"
            f"duration=0.8:offset={offset:.3f},format=yuv420p[v]"
        )
        new_dur=current_dur+nxt_dur-0.8
        run([ffmpeg,"-y","-i",str(current),"-i",str(nxt),
             "-filter_complex",filter_complex,
             "-map","[v]","-an","-c:v","libx264","-preset","veryfast",
             "-crf","23","-pix_fmt","yuv420p",str(out)],timeout=900)
        current=out
        current_dur=new_dur

    run([ffmpeg,"-y","-i",str(current),"-i",str(VOICE),
         "-map","0:v:0","-map","1:a:0",
         "-c:v","copy","-c:a","aac","-b:a","128k",
         "-shortest",str(VIDEO)],timeout=900)


def main():
    OUT.mkdir(exist_ok=True)
    SCENES.mkdir(exist_ok=True)
    DEITIES.mkdir(exist_ok=True)

    # Clean renderer-generated clips only.
    for p in SCENES.glob("*"):
        if p.is_file():
            p.unlink()

    script=get_script()
    sections=rashi_sections(script)
    deity_paths=prepare_deities()

    asyncio.run(make_voice(script))
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    duration=audio_duration(ffmpeg)
    print("Narration:",duration,"seconds")

    intro=SCENES/"000_intro.jpg"
    create_intro(intro)
    scenes=[intro]

    for i,(rashi,emoji,deity) in enumerate(RASHIS,1):
        content=sections.get(
            rashi,
            f"{rashi} राशि: आज के ग्रह गोचर के महत्वपूर्ण संकेत।"
        )
        p=SCENES/f"{i:03d}_{rashi}.jpg"
        create_scene(rashi,emoji,deity,content,deity_paths[deity],p)
        scenes.append(p)

    final=SCENES/"999_final.jpg"
    create_final(final)
    scenes.append(final)

    build_video(ffmpeg,scenes,duration)

    print("==========================================")
    print("VIDEO COMPLETE")
    print(VIDEO)
    print("==========================================")


if __name__=="__main__":
    main()
