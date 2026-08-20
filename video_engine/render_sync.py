"""Production renderer for the Daily Astro Hindi channel.

Design rules:
- The narration is the master timeline.
- Exactly 14 audio segments: intro + 12 Rashis + outro.
- A Rashi visual exists only during that Rashi's narration segment.
- No crossfade overlap between Rashis, so the next Rashi cannot appear early.
- The opening artwork is rebuilt from the ORIGINAL TOP portion only; the
  duplicated/mirrored lower half of the old intro artwork is deliberately
  discarded.
- Deity names are NOT printed underneath deity photographs.
- Deity artwork is loaded only from bundled assets/deities; no remote image
  download is performed during rendering.
"""

from pathlib import Path
import asyncio
import json
import re
import subprocess

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from . import render as base

OUTPUT = base.OUTPUT
SCENES = base.SCENES
VOICE = base.VOICE
VIDEO = base.VIDEO
SYNC_DIR = OUTPUT / "audio_segments"
MANIFEST = OUTPUT / "sync_manifest.json"

VOICE_NAME = base.VOICE_NAME
FPS = base.FPS
WIDTH = base.WIDTH
HEIGHT = base.HEIGHT
FADE_SECONDS = 0.32

DEITY_FILES = {
    "हनुमान जी": "hanuman.jpg",
    "महालक्ष्मी जी": "lakshmi.jpg",
    "श्री गणेश जी": "ganesha.jpg",
    "भगवान शिव": "shiva.jpg",
    "सूर्य देव": "surya.jpg",
    "भगवान विष्णु": "vishnu.jpg",
    "शनि देव": "shani.jpg",
}


def run(cmd, timeout=1800):
    result = subprocess.run(
        [str(x) for x in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(result.stdout[-12000:])
    return result.stdout


def duration(ffmpeg, path: Path) -> float:
    result = subprocess.run(
        [ffmpeg, "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not m:
        raise RuntimeError(f"Could not determine duration: {path}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


async def synthesize(text: str, path: Path):
    await edge_tts.Communicate(
        text, VOICE_NAME, rate="+5%", volume="+0%"
    ).save(str(path))


def clean_text(text: str) -> str:
    return " ".join(x.strip() for x in text.splitlines() if x.strip())


def split_script(script: str):
    """Return intro + 12 canonical Rashi sections + outro."""
    lines = script.splitlines()
    starts = []
    for idx, (key, label, deity, query) in enumerate(base.RASHIS):
        pattern = re.compile(rf"^\s*{re.escape(key)}\s+राशि(?:[।:]|\s)")
        matches = [n for n, line in enumerate(lines) if pattern.search(line)]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one {key} राशि heading; found {len(matches)}")
        starts.append((matches[0], idx, key, label))

    starts.sort()
    if [x[1] for x in starts] != list(range(12)):
        raise RuntimeError("Rashi headings are not in canonical order")

    intro = clean_text("\n".join(lines[:starts[0][0]]))
    segments = [("intro", "प्रस्तावना", intro)]

    for pos, (line_no, idx, key, label) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        segments.append((key, label, clean_text("\n".join(lines[line_no:end]))))

    # Split the disclaimer/CTA from Meen so it cannot appear over the Meen card.
    last_key, last_label, last_body = segments[-1]
    marker = re.search(r"(यह सामान्य चंद्र राशि आधारित.*)$", last_body, re.DOTALL)
    if marker:
        segments[-1] = (last_key, last_label, clean_text(last_body[:marker.start()]))
        outro = clean_text(marker.group(1))
    else:
        outro = (
            "यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है; "
            "व्यक्तिगत फलादेश के लिए जन्म कुंडली और दशा का अध्ययन आवश्यक होता है। "
            "वीडियो उपयोगी लगे तो लाइक, फॉलो और सब्सक्राइब करें। "
            "कल फिर मिलेंगे नए ग्रह संकेतों के साथ। नमस्कार!"
        )

    segments.append(("outro", "समापन", outro))
    if len(segments) != 14 or any(not x[2] for x in segments):
        raise RuntimeError("Expected 14 non-empty narration segments")
    return segments


def font(size):
    return base.get_font(size)


def fit_text(draw, text, max_width, start_size, min_size=22):
    size = start_size
    while size >= min_size:
        f = font(size)
        box = draw.textbbox((0, 0), text, font=f)
        if box[2] - box[0] <= max_width:
            return f
        size -= 2
    return font(min_size)


def wrap_devanagari(text, max_chars=34):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def gradient_canvas():
    img = Image.new("RGB", (WIDTH, HEIGHT), (12, 4, 24))
    px = img.load()
    for y in range(HEIGHT):
        p = y / HEIGHT
        r = int(18 + 28 * p)
        g = int(4 + 4 * p)
        b = int(32 + 22 * p)
        for x in range(WIDTH):
            # subtle warm center glow
            dx = abs(x - WIDTH / 2) / (WIDTH / 2)
            glow = int(max(0, 18 * (1 - dx) * (1 - p)))
            px[x, y] = (min(255, r + glow), g, min(255, b + glow))
    return img


def paste_hero(canvas, source, box):
    left, top, right, bottom = box
    w, h = right - left, bottom - top
    src = ImageOps.exif_transpose(source.convert("RGB"))
    fitted = base.crop_cover(src, w, h)
    fitted = ImageEnhance.Color(fitted).enhance(1.06)
    fitted = ImageEnhance.Contrast(fitted).enhance(1.04)
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=255)
    canvas.paste(fitted, (left, top), mask)
    return canvas


def create_intro(script_text):
    """Build a new opening from the TOP artwork only; never show its duplicate."""
    out = SCENES / "000_intro.jpg"
    source_path = base.INTRO_ASSET
    if not source_path.exists():
        raise RuntimeError(f"Missing intro artwork: {source_path}")

    source = ImageOps.exif_transpose(Image.open(source_path).convert("RGB"))
    # The old asset contains a second mirrored copy below the real hero.
    # Keep only the upper 54%, where the original devotional artwork lives.
    top_only = source.crop((0, 0, source.width, int(source.height * 0.54)))

    canvas = gradient_canvas().convert("RGBA")
    # Hero image occupies the upper portion, with a soft blurred backing.
    hero = base.crop_cover(top_only, WIDTH - 80, 1050)
    blurred = hero.filter(ImageFilter.GaussianBlur(24)).convert("RGBA")
    blurred.putalpha(150)
    canvas.alpha_composite(blurred, (40, 120))
    canvas.alpha_composite(hero.convert("RGBA"), (40, 120))

    draw = ImageDraw.Draw(canvas)
    gold = (247, 202, 77, 255)
    cream = (255, 244, 214, 255)
    white = (255, 250, 240, 255)
    panel = (23, 7, 30, 235)

    draw.rounded_rectangle((28, 28, WIDTH - 28, HEIGHT - 28), radius=42, outline=gold, width=4)
    title = "॥ दैनिक वैदिक ज्योतिष ॥"
    tf = fit_text(draw, title, WIDTH - 120, 66, 42)
    tb = draw.textbbox((0, 0), title, font=tf)
    draw.text(((WIDTH - (tb[2] - tb[0])) / 2, 1180), title, font=tf, fill=cream)

    date_line = next((x.strip() for x in script_text.splitlines() if x.strip().startswith("आज ")), "आज का दैनिक राशिफल")
    df = fit_text(draw, date_line, WIDTH - 150, 38, 26)
    draw.rounded_rectangle((70, 1280, WIDTH - 70, 1365), radius=28, fill=panel, outline=gold, width=2)
    db = draw.textbbox((0, 0), date_line, font=df)
    draw.text(((WIDTH - (db[2] - db[0])) / 2, 1302), date_line, font=df, fill=white)

    transition_line = next((x.strip() for x in script_text.splitlines() if "राशि में प्रवेश" in x or "गोचर" in x), "")
    if transition_line:
        transition = "आज का प्रमुख गोचर\n" + transition_line
        lines = wrap_devanagari(transition, 42)
        y = 1425
        draw.rounded_rectangle((55, 1400, WIDTH - 55, 1620), radius=30, fill=panel, outline=(220, 174, 65, 220), width=2)
        for line in lines[:4]:
            f = fit_text(draw, line, WIDTH - 130, 31, 23)
            bb = draw.textbbox((0, 0), line, font=f)
            draw.text(((WIDTH - (bb[2] - bb[0])) / 2, y), line, font=f, fill=cream)
            y += 48

    hook = "ॐ  •  आस्था  •  ग्रह गोचर  •  शुभ संकेत  •  ॐ"
    hf = fit_text(draw, hook, WIDTH - 100, 29, 21)
    hb = draw.textbbox((0, 0), hook, font=hf)
    draw.text(((WIDTH - (hb[2] - hb[0])) / 2, 1660), hook, font=hf, fill=gold)
    footer = "बारहों राशियों के लिए आज के ग्रह संकेत"
    ff = fit_text(draw, footer, WIDTH - 100, 27, 20)
    fb = draw.textbbox((0, 0), footer, font=ff)
    draw.text(((WIDTH - (fb[2] - fb[0])) / 2, 1770), footer, font=ff, fill=white)

    canvas.convert("RGB").save(out, "JPEG", quality=97, subsampling=0)
    return out


def create_rashi_scene(index, key, label, deity, deity_path, text):
    out = SCENES / f"{index:03d}_{key}.jpg"
    canvas = gradient_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    gold = (247, 202, 77, 255)
    cream = (255, 244, 214, 255)
    white = (255, 250, 242, 255)
    panel = (14, 5, 24, 238)

    draw.rounded_rectangle((28, 28, WIDTH - 28, HEIGHT - 28), radius=42, outline=gold, width=4)
    draw.text((70, 70), "ॐ", font=font(58), fill=gold)
    title = label
    tf = fit_text(draw, title, WIDTH - 240, 62, 42)
    tb = draw.textbbox((0, 0), title, font=tf)
    draw.text(((WIDTH - (tb[2] - tb[0])) / 2, 72), title, font=tf, fill=cream)
    draw.text((WIDTH - 130, 72), "ॐ", font=font(58), fill=gold)

    # Deity image: prominent, correctly oriented, no deity name beneath it.
    source = ImageOps.exif_transpose(Image.open(deity_path).convert("RGB"))
    hero_box = (55, 180, WIDTH - 55, 1030)
    paste_hero(canvas, source, hero_box)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(hero_box, radius=34, outline=gold, width=3)

    # A subtle devotional halo, but no textual deity label.
    draw.ellipse((WIDTH//2 - 34, 100, WIDTH//2 + 34, 168), fill=gold)

    # Content card. The spoken section is the exact text associated with this card.
    card = (55, 1090, WIDTH - 55, 1780)
    draw.rounded_rectangle(card, radius=32, fill=panel, outline=(208, 164, 62, 220), width=2)
    header = "आज के ग्रह संकेत"
    hf = fit_text(draw, header, WIDTH - 150, 35, 25)
    hb = draw.textbbox((0, 0), header, font=hf)
    draw.text(((WIDTH - (hb[2] - hb[0])) / 2, 1130), header, font=hf, fill=gold)

    # Remove the heading itself from the body to avoid repeating the Rashi label.
    body = text
    body = re.sub(rf"^\s*{re.escape(key)}\s+राशि[।:\s]*", "", body).strip()
    lines = wrap_devanagari(body, 38)
    y = 1195
    bf = font(29)
    max_lines = 16
    for line in lines[:max_lines]:
        draw.text((95, y), line, font=bf, fill=white)
        y += 38

    footer = "आज के लिए धैर्य • कर्म • विश्वास • सकारात्मक सोच"
    ff = fit_text(draw, footer, WIDTH - 120, 25, 19)
    fb = draw.textbbox((0, 0), footer, font=ff)
    draw.text(((WIDTH - (fb[2] - fb[0])) / 2, 1840), footer, font=ff, fill=gold)

    canvas.convert("RGB").save(out, "JPEG", quality=97, subsampling=0)
    return out


def create_outro():
    out = SCENES / "999_outro.jpg"
    canvas = gradient_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    gold = (247, 202, 77, 255)
    cream = (255, 244, 214, 255)
    draw.rounded_rectangle((28, 28, WIDTH - 28, HEIGHT - 28), radius=42, outline=gold, width=4)
    draw.text((WIDTH//2 - 55, 420), "ॐ", font=font(100), fill=gold)
    title = "॥ शुभम् भवतु ॥"
    f = fit_text(draw, title, WIDTH - 150, 64, 42)
    bb = draw.textbbox((0, 0), title, font=f)
    draw.text(((WIDTH - (bb[2] - bb[0])) / 2, 610), title, font=f, fill=cream)
    lines = ["आपका दिन शुभ और मंगलमय हो", "ईश्वर की कृपा और सकारात्मक ऊर्जा आपके साथ रहे", "कल फिर मिलेंगे नए ग्रह संकेतों के साथ"]
    y = 800
    for line in lines:
        f = fit_text(draw, line, WIDTH - 180, 34, 24)
        bb = draw.textbbox((0, 0), line, font=f)
        draw.text(((WIDTH - (bb[2] - bb[0])) / 2, y), line, font=f, fill=cream)
        y += 75
    draw.text((WIDTH//2 - 40, 1160), "ॐ", font=font(70), fill=gold)
    canvas.convert("RGB").save(out, "JPEG", quality=97, subsampling=0)
    return out


def make_motion_clip(ffmpeg, scene, seconds, index):
    out = SCENES / f"clip_sync_{index:02d}.mp4"
    frames = max(2, round(seconds * FPS))
    # Very slow push-in; alternating horizontal drift prevents a static slideshow.
    z = "min(1.10,1+0.00008*on)"
    if index % 2:
        x = f"(iw-iw/zoom)*(on/{frames})"
    else:
        x = f"(iw-iw/zoom)*(1-on/{frames})"
    y = "(ih-ih/zoom)/2"
    fi = min(FADE_SECONDS, max(0.08, seconds / 5))
    fo = max(0.0, seconds - fi)
    vf = (
        f"zoompan=z={z}:x={x}:y={y}:d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"fade=t=in:st=0:d={fi:.3f},fade=t=out:st={fo:.3f}:d={fi:.3f}"
    )
    run([
        ffmpeg, "-y", "-loop", "1", "-i", scene,
        "-vf", vf, "-t", f"{seconds:.3f}", "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", out,
    ], timeout=900)
    return out


def concat_video(ffmpeg, clips):
    out = SCENES / "video_no_audio_sync.mp4"
    args = [ffmpeg, "-y"]
    labels = []
    for i, clip in enumerate(clips):
        args += ["-i", clip]
        labels.append(f"[{i}:v]")
    args += [
        "-filter_complex", "".join(labels) + f"concat=n={len(clips)}:v=1:a=0[v]",
        "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", out,
    ]
    run(args, timeout=1800)
    return out


def concat_audio(ffmpeg, files):
    args = [ffmpeg, "-y"]
    labels = []
    for i, path in enumerate(files):
        args += ["-i", path]
        labels.append(f"[{i}:a]")
    args += [
        "-filter_complex", "".join(labels) + f"concat=n={len(files)}:v=0:a=1[a]",
        "-map", "[a]", "-c:a", "libmp3lame", "-b:a", "128k", VOICE,
    ]
    run(args, timeout=1800)


def attach_audio(ffmpeg, video, seconds):
    run([
        ffmpeg, "-y", "-i", video, "-i", VOICE,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-t", f"{seconds:.3f}", VIDEO,
    ], timeout=1800)


def validate(ffmpeg, audio_total, scene_durations):
    video_total = duration(ffmpeg, VIDEO)
    delta = abs(video_total - audio_total)
    print(f"FINAL SYNC: video={video_total:.3f}s audio={audio_total:.3f}s delta={delta:.3f}s")
    if delta > 0.20:
        raise RuntimeError("Final audio/video duration mismatch > 0.20s")
    if len(scene_durations) != 14 or any(x <= 0 for x in scene_durations):
        raise RuntimeError("Invalid 14-segment timeline")


def validate_deities():
    root = Path("assets/deities")
    paths = {}
    for deity, filename in DEITY_FILES.items():
        p = root / filename
        if not p.exists():
            raise RuntimeError(f"Missing bundled deity artwork: {p}")
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im)
            print(f"DEITY {deity}: {im.size}")
            # Require a genuinely large source. The workflow separately checks 1200px;
            # this renderer refuses tiny/thumbnail assets.
            if min(im.width, im.height) < 1200:
                raise RuntimeError(f"Deity artwork too small: {p} -> {im.size}")
        paths[deity] = p
    return paths


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    SCENES.mkdir(parents=True, exist_ok=True)
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    for p in SYNC_DIR.glob("*.mp3"):
        p.unlink()

    script = base.load_script()
    segments = split_script(script)
    print("Loaded daily_script.md")
    print("Timeline: intro -> Mesha -> Vrishabha -> Mithun -> Karka -> Simha -> Kanya -> Tula -> Vrishchik -> Dhanu -> Makar -> Kumbh -> Meen -> outro")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    audio_files, durations = [], []
    manifest = []
    cursor = 0.0

    for i, (key, label, text) in enumerate(segments):
        path = SYNC_DIR / f"{i:02d}_{key}.mp3"
        print(f"TTS {i+1}/14: {label}")
        asyncio.run(synthesize(text, path))
        sec = duration(ffmpeg, path)
        audio_files.append(path)
        durations.append(sec)
        manifest.append({
            "index": i, "key": key, "label": label,
            "start_seconds": round(cursor, 3),
            "end_seconds": round(cursor + sec, 3),
            "audio_seconds": round(sec, 3),
            "text": text,
        })
        cursor += sec

    concat_audio(ffmpeg, audio_files)
    audio_total = duration(ffmpeg, VOICE)

    deity_paths = validate_deities()
    scenes = [create_intro(script)]
    for i, (key, label, deity, query) in enumerate(base.RASHIS, start=1):
        text = next(x[2] for x in segments if x[0] == key)
        scenes.append(create_rashi_scene(i, key, label, deity, deity_paths[deity], text))
    scenes.append(create_outro())

    if len(scenes) != 14:
        raise RuntimeError(f"Expected 14 visual scenes, got {len(scenes)}")
    for item, scene in zip(manifest, scenes):
        item["scene"] = str(scene)
        item["scene_seconds"] = item["audio_seconds"]

    clips = []
    for i, (scene, sec) in enumerate(zip(scenes, durations)):
        print(f"VIDEO {i+1}/14: {manifest[i]['label']} {sec:.3f}s")
        clips.append(make_motion_clip(ffmpeg, scene, sec, i))

    silent = concat_video(ffmpeg, clips)
    attach_audio(ffmpeg, silent, audio_total)
    validate(ffmpeg, audio_total, durations)

    Image.open(scenes[0]).save(OUTPUT / "video_poster.png", "PNG")
    MANIFEST.write_text(json.dumps({
        "method": "audio-led-exact-boundary-v3",
        "transition_type": "contained_fade_no_overlap",
        "total_audio_seconds": round(audio_total, 3),
        "segments": manifest,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("AUDIO-LED DEVOTIONAL VIDEO COMPLETE")
    print(f"VIDEO={VIDEO}")
    print(f"VOICE={VOICE}")
    print(f"MANIFEST={MANIFEST}")


if __name__ == "__main__":
    main()
