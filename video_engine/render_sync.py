"""Audio-led devotional renderer.

The generated TTS segments are the master timeline. Each visual scene is
rendered for exactly the duration of its corresponding narration segment.
No fixed zodiac slideshow timing is used.
"""
from pathlib import Path
import asyncio
import json
import re
import subprocess

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

VERSION = "V6-AUDIO-LED-DEVOTIONAL"
OUT = Path("output")
SCENES = OUT / "video_scenes"
SEGDIR = OUT / "audio_segments"
SCRIPT = OUT / "daily_script.md"
VOICE = OUT / "daily_voice.mp3"
VIDEO = OUT / "daily_video.mp4"
MANIFEST = OUT / "sync_manifest.json"
POSTER = OUT / "video_poster.png"
CREDITS = OUT / "deity_credits.txt"
ASSETS = Path("assets")
DEITY_DIR = ASSETS / "deities"
INTRO_ASSET = ASSETS / "intro_devotional.jpg"
FONT_PATH = ASSETS / "NotoSansDevanagari-Regular.ttf"
W, H, FPS = 1080, 1920, 30
VOICE_NAME = "hi-IN-SwaraNeural"
RASHIS = [
    ("मेष", "मेष राशि", "हनुमान जी", "hanuman.jpg"),
    ("वृषभ", "वृषभ राशि", "महालक्ष्मी जी", "lakshmi.jpg"),
    ("मिथुन", "मिथुन राशि", "श्री गणेश जी", "ganesha.jpg"),
    ("कर्क", "कर्क राशि", "भगवान शिव", "shiva.jpg"),
    ("सिंह", "सिंह राशि", "सूर्य देव", "surya.jpg"),
    ("कन्या", "कन्या राशि", "श्री गणेश जी", "ganesha.jpg"),
    ("तुला", "तुला राशि", "महालक्ष्मी जी", "lakshmi.jpg"),
    ("वृश्चिक", "वृश्चिक राशि", "हनुमान जी", "hanuman.jpg"),
    ("धनु", "धनु राशि", "भगवान विष्णु", "vishnu.jpg"),
    ("मकर", "मकर राशि", "शनि देव", "shani.jpg"),
    ("कुंभ", "कुंभ राशि", "शनि देव", "shani.jpg"),
    ("मीन", "मीन राशि", "भगवान विष्णु", "vishnu.jpg"),
]


def run(cmd, timeout=1800):
    print("RUN:", " ".join(str(x) for x in cmd))
    r = subprocess.run([str(x) for x in cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    print(r.stdout[-6000:])
    if r.returncode:
        raise RuntimeError(r.stdout[-12000:])


def duration(ff, path):
    r = subprocess.run([ff, "-i", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    if not m:
        raise RuntimeError(f"Cannot read duration: {path}")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def font(size):
    return ImageFont.truetype(str(FONT_PATH), size)


def crop_cover(img, width, height):
    img = img.convert("RGB")
    scale = max(width / img.width, height / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = max(0, (nw - width) // 2), max(0, (nh - height) // 2)
    return img.crop((left, top, left + width, top + height))


def wrap(text, limit=38):
    out, cur = [], ""
    for word in text.split():
        candidate = word if not cur else cur + " " + word
        if len(candidate) <= limit:
            cur = candidate
        else:
            if cur: out.append(cur)
            cur = word
    if cur: out.append(cur)
    return out


def fit(draw, text, max_width, size, minimum=20):
    for n in range(size, minimum - 1, -2):
        f = font(n)
        b = draw.textbbox((0, 0), text, font=f)
        if b[2] - b[0] <= max_width:
            return f
    return font(minimum)


def clean(text):
    return " ".join(x.strip() for x in text.splitlines() if x.strip())


def split_script(script):
    lines = script.splitlines()
    starts = []
    for idx, (key, label, deity, filename) in enumerate(RASHIS):
        hits = [i for i, line in enumerate(lines) if re.match(rf"^\s*{re.escape(key)}\s+राशि(?:[।:]|\s)", line)]
        if len(hits) != 1:
            raise RuntimeError(f"Expected exactly one {key} राशि line; found {len(hits)}")
        starts.append((hits[0], idx, key, label))
    starts.sort()
    if [x[1] for x in starts] != list(range(12)):
        raise RuntimeError("Rashi narration is not in canonical order")
    segments = [("intro", "प्रस्तावना", clean("\n".join(lines[:starts[0][0])))]
    for n, (line, idx, key, label) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        segments.append((key, label, clean("\n".join(lines[line:end]))))
    last_key, last_label, last_text = segments[-1]
    m = re.search(r"(यह सामान्य चंद्र राशि आधारित.*)$", last_text, re.S)
    if m:
        segments[-1] = (last_key, last_label, clean(last_text[:m.start()]))
        outro = clean(m.group(1))
    else:
        outro = "यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है। व्यक्तिगत फलादेश के लिए जन्म कुंडली का अध्ययन आवश्यक होता है। वीडियो उपयोगी लगे तो लाइक, फॉलो और सब्सक्राइब करें। कल फिर मिलेंगे। नमस्कार!"
    segments.append(("outro", "समापन", outro))
    if len(segments) != 14 or any(not x[2] for x in segments):
        raise RuntimeError("Expected 14 non-empty narration segments")
    return segments


def reset_outputs():
    OUT.mkdir(exist_ok=True); SCENES.mkdir(exist_ok=True); SEGDIR.mkdir(exist_ok=True)
    for p in list(SCENES.glob("*")) + list(SEGDIR.glob("*")):
        if p.is_file(): p.unlink()
    for p in (VIDEO, VOICE, MANIFEST, POSTER):
        if p.exists(): p.unlink()


def validate_assets():
    if not FONT_PATH.exists(): raise RuntimeError(f"Missing font: {FONT_PATH}")
    if not INTRO_ASSET.exists(): raise RuntimeError(f"Missing intro artwork: {INTRO_ASSET}")
    paths = {}
    for deity, _, _, filename in RASHIS:
        p = DEITY_DIR / filename
        if not p.exists(): raise RuntimeError(f"Missing deity artwork: {p}")
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im)
            print(f"HD deity asset: {deity} -> {im.size}")
            if min(im.size) < 1200: raise RuntimeError(f"Deity artwork below 1200px: {p} -> {im.size}")
        paths[filename] = p
    CREDITS.write_text("Bundled local devotional artwork.\nNo remote deity-image download is used.\n", encoding="utf-8")
    return paths


def background():
    return Image.new("RGBA", (W, H), (18, 5, 30, 255))


def intro_scene(script):
    out = SCENES / "000_intro.jpg"
    src = ImageOps.exif_transpose(Image.open(INTRO_ASSET).convert("RGB"))
    hero = crop_cover(src, W - 80, 1120)
    canvas = background()
    blur = hero.filter(ImageFilter.GaussianBlur(24)).convert("RGBA"); blur.putalpha(110)
    canvas.alpha_composite(blur, (40, 80)); canvas.alpha_composite(hero.convert("RGBA"), (40, 80))
    d = ImageDraw.Draw(canvas); gold=(247,202,77,255); cream=(255,244,214,255); panel=(20,4,28,235)
    d.rounded_rectangle((24,24,W-24,H-24), radius=42, outline=gold, width=4)
    title="॥ दैनिक वैदिक ज्योतिष ॥"; f=fit(d,title,W-100,66,42); b=d.textbbox((0,0),title,font=f); d.text(((W-b[2]+b[0])/2,1260),title,font=f,fill=cream)
    date=next((x.strip() for x in script.splitlines() if x.strip().startswith("आज ")),"आज का दैनिक राशिफल")
    date=" ".join(date.split())
    f=fit(d,date,W-150,34,22); b=d.textbbox((0,0),date,font=f); d.rounded_rectangle((55,1350,W-55,1435),radius=28,fill=panel,outline=gold,width=2); d.text(((W-b[2]+b[0])/2,1373),date,font=f,fill=cream)
    hook="ॐ  •  आस्था  •  ग्रह गोचर  •  शुभ संकेत  •  ॐ"; f=fit(d,hook,W-100,30,20); b=d.textbbox((0,0),hook,font=f); d.text(((W-b[2]+b[0])/2,1510),hook,font=f,fill=gold)
    sub="बारहों राशियों के लिए आज के ग्रह संकेत"; f=fit(d,sub,W-100,30,20); b=d.textbbox((0,0),sub,font=f); d.text(((W-b[2]+b[0])/2,1660),sub,font=f,fill=cream)
    canvas.convert("RGB").save(out,"JPEG",quality=98,subsampling=0); return out


def rashi_scene(index, key, label, deity, path, narration):
    out=SCENES/f"{index:03d}_{key}.jpg"; canvas=background(); d=ImageDraw.Draw(canvas)
    gold=(247,202,77,255); cream=(255,244,214,255); white=(255,250,242,255); panel=(12,4,24,242)
    # Deity artwork is oriented with EXIF and displayed once; no deity name below it.
    src=ImageOps.exif_transpose(Image.open(path).convert("RGB"))
    bg=crop_cover(src,W,H).filter(ImageFilter.GaussianBlur(28)); bg=ImageEnhance.Brightness(bg).enhance(.30); canvas.alpha_composite(bg.convert("RGBA"))
    canvas.alpha_composite(Image.new("RGBA",(W,H),(18,5,30,125)))
    d=ImageDraw.Draw(canvas); d.rounded_rectangle((24,24,W-24,H-24),radius=42,outline=gold,width=4)
    f=fit(d,label,W-260,62,40); b=d.textbbox((0,0),label,font=f); d.rounded_rectangle((45,45,W-45,155),radius=30,fill=panel,outline=gold,width=2); d.text(((W-b[2]+b[0])/2,67),label,font=f,fill=cream)
    hero=crop_cover(src,900,820); mask=Image.new("L",(900,820)); ImageDraw.Draw(mask).rounded_rectangle((0,0,899,819),radius=38,fill=255); canvas.paste(hero,(90,205),mask); d=ImageDraw.Draw(canvas); d.rounded_rectangle((90,205,990,1025),radius=38,outline=gold,width=5)
    # No text under the deity image.
    d.rounded_rectangle((50,1090,W-50,1785),radius=32,fill=panel,outline=gold,width=2); head="आज के ग्रह गोचर के संकेत"; f=fit(d,head,W-140,34,24); b=d.textbbox((0,0),head,font=f); d.text(((W-b[2]+b[0])/2,1130),head,font=f,fill=gold)
    body=re.sub(rf"^\s*{re.escape(key)}\s+राशि[।:\s]*","",narration).strip(); y=1190
    for line in wrap(body,38)[:12]: d.text((85,y),line,font=font(30),fill=white); y+=43
    footer="॥ श्रद्धा • विश्वास • सकारात्मक ऊर्जा • वैदिक ज्योतिष ॥"; f=fit(d,footer,W-100,24,18); b=d.textbbox((0,0),footer,font=f); d.text(((W-b[2]+b[0])/2,1840),footer,font=f,fill=gold)
    canvas.convert("RGB").save(out,"JPEG",quality=98,subsampling=0); return out


def outro_scene():
    out=SCENES/"999_outro.jpg"; c=background(); d=ImageDraw.Draw(c); gold=(247,202,77,255); cream=(255,244,214,255)
    d.rounded_rectangle((24,24,W-24,H-24),radius=42,outline=gold,width=4); d.text((W//2-55,420),"ॐ",font=font(100),fill=gold)
    title="॥ शुभम् भवतु ॥"; f=fit(d,title,W-160,64,42); b=d.textbbox((0,0),title,font=f); d.text(((W-b[2]+b[0])/2,620),title,font=f,fill=cream)
    y=820
    for line in ["आपका दिन शुभ और मंगलमय हो","ईश्वर की कृपा और सकारात्मक ऊर्जा आपके साथ रहे","कल फिर मिलेंगे नए ग्रह संकेतों के साथ"]:
        f=fit(d,line,W-180,34,24); b=d.textbbox((0,0),line,font=f); d.text(((W-b[2]+b[0])/2,y),line,font=f,fill=cream); y+=80
    c.convert("RGB").save(out,"JPEG",quality=98,subsampling=0); return out


async def tts(text, path):
    await edge_tts.Communicate(text, VOICE_NAME, rate="+5%", volume="+0%").save(str(path))


def motion(ff, scene, seconds, index):
    out=SCENES/f"motion_{index:02d}.mp4"; frames=max(2,round(seconds*FPS)); zoom="min(1.13,1+0.00010*on)"; x="(iw-iw/zoom)/2"; y="(ih-ih/zoom)/2"; fade=min(.28,max(.10,seconds/6)); fo=max(.05,seconds-fade)
    vf=f"zoompan=z={zoom}:x={x}:y={y}:d={frames}:s={W}x{H}:fps={FPS},fade=t=in:st=0:d={fade:.3f},fade=t=out:st={fo:.3f}:d={fade:.3f}"
    run([ff,"-y","-loop","1","-i",scene,"-vf",vf,"-t",f"{seconds:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",out],900); return out


def concat_video(ff, clips):
    out=SCENES/"video_no_audio_sync.mp4"; args=[ff,"-y"]; labels=[]
    for i,p in enumerate(clips): args += ["-i",p]; labels.append(f"[{i}:v]")
    args += ["-filter_complex","".join(labels)+f"concat=n={len(clips)}:v=1:a=0[v]","-map","[v]","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",out]; run(args,1800); return out


def concat_audio(ff, files):
    args=[ff,"-y"]; labels=[]
    for i,p in enumerate(files): args += ["-i",p]; labels.append(f"[{i}:a]")
    args += ["-filter_complex","".join(labels)+f"concat=n={len(files)}:v=0:a=1[a]","-map","[a]","-c:a","libmp3lame","-b:a","160k",VOICE]; run(args,1800)


def attach(ff, silent, total):
    run([ff,"-y","-i",silent,"-i",VOICE,"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","160k","-t",f"{total:.3f}",VIDEO],1800)


def main():
    reset_outputs(); paths=validate_assets(); ff=imageio_ffmpeg.get_ffmpeg_exe()
    script=SCRIPT.read_text(encoding="utf-8").strip() if SCRIPT.exists() else ""
    if not script: raise RuntimeError("output/daily_script.md is missing or empty")
    segments=split_script(script)
    audio_files=[]; durations=[]; manifest=[]; cursor=0.0
    for i,(key,label,text) in enumerate(segments):
        p=SEGDIR/f"{i:02d}_{key}.mp3"; print(f"TTS {i+1}/14: {label}"); asyncio.run(tts(text,p)); sec=duration(ff,p); audio_files.append(p); durations.append(sec); manifest.append({"index":i,"key":key,"label":label,"start_seconds":round(cursor,3),"end_seconds":round(cursor+sec,3),"audio_seconds":round(sec,3),"text":text}); cursor+=sec
    concat_audio(ff,audio_files); total_audio=duration(ff,VOICE)
    scenes=[intro_scene(script)]
    for i,(key,label,deity,filename) in enumerate(RASHIS,1):
        narration=next(x[2] for x in segments if x[0]==key); scenes.append(rashi_scene(i,key,label,deity,paths[filename],narration))
    scenes.append(outro_scene())
    if len(scenes)!=14: raise RuntimeError("Scene count does not match 14 narration segments")
    clips=[]
    for i,(scene,sec) in enumerate(zip(scenes,durations)):
        manifest[i]["scene_seconds"]=round(sec,3); manifest[i]["scene"]=str(scene); clips.append(motion(ff,scene,sec,i))
    silent=concat_video(ff,clips); attach(ff,silent,total_audio); total_video=duration(ff,VIDEO); delta=abs(total_video-total_audio)
    print(f"{VERSION}: audio={total_audio:.3f}s video={total_video:.3f}s delta={delta:.3f}s")
    if delta>0.20: raise RuntimeError("FINAL AUDIO/VIDEO SYNC FAILED")
    Image.open(scenes[0]).save(POSTER,"PNG")
    MANIFEST.write_text(json.dumps({"renderer":VERSION,"method":"audio-segment-duration-is-master-timeline","transition":"per-segment fade, zero overlap","total_audio_seconds":round(total_audio,3),"total_video_seconds":round(total_video,3),"segments":manifest},ensure_ascii=False,indent=2),encoding="utf-8")
    print("PRODUCTION VIDEO COMPLETE")

if __name__ == "__main__": main()
