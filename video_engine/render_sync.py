"""Production renderer: narration segments are the master timeline.

Each visual scene is rendered for exactly the duration of its matching TTS
segment. There is no fixed-duration zodiac slideshow, so a rashi cannot
appear before its narration starts.
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

VERSION = "V5-AUDIO-LED-DEVOTIONAL"
OUT = base.OUTPUT
SCENES = base.SCENES
VOICE = base.VOICE
VIDEO = base.VIDEO
SEGDIR = OUT / "audio_segments"
MANIFEST = OUT / "sync_manifest.json"
W, H, FPS = base.WIDTH, base.HEIGHT, base.FPS

DEITIES = {
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
    print(result.stdout[-6000:])
    if result.returncode != 0:
        raise RuntimeError(result.stdout[-12000:])


def media_duration(ffmpeg, path):
    result = subprocess.run(
        [ffmpeg, "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"Cannot read media duration: {path}")
    return int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])


async def speak(text, path):
    await edge_tts.Communicate(
        text,
        base.VOICE_NAME,
        rate="+5%",
        volume="+0%",
    ).save(str(path))


def clean(text):
    return " ".join(line.strip() for line in text.splitlines() if line.strip())


def font(size):
    return base.get_font(size)


def fit(draw, text, max_width, size, minimum=20):
    current = size
    while current >= minimum:
        fnt = font(current)
        box = draw.textbbox((0, 0), text, font=fnt)
        if box[2] - box[0] <= max_width:
            return fnt
        current -= 2
    return font(minimum)


def wrap(text, limit=38):
    result = []
    current = ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                result.append(current)
            current = word
    if current:
        result.append(current)
    return result


def split_script(script):
    """Return intro + 12 canonical rashi segments + outro."""
    lines = script.splitlines()
    starts = []

    for index, (key, label, deity, query) in enumerate(base.RASHIS):
        hits = [
            line_no
            for line_no, line in enumerate(lines)
            if re.search(
                rf"^\s*{re.escape(key)}\s+राशि(?:[।:]|\s)",
                line,
            )
        ]
        if len(hits) != 1:
            raise RuntimeError(
                f"Expected exactly one heading for {key} राशि; found {len(hits)}"
            )
        starts.append((hits[0], index, key, label))

    starts.sort(key=lambda item: item[0])
    if [item[1] for item in starts] != list(range(12)):
        raise RuntimeError("Rashi headings are not in canonical order")

    segments = []
    intro_text = clean("\n".join(lines[: starts[0][0]]))
    segments.append(("intro", "प्रस्तावना", intro_text))

    for position, (line_no, _index, key, label) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        text = clean("\n".join(lines[line_no:end]))
        segments.append((key, label, text))

    key, label, last = segments[-1]
    match = re.search(r"(यह सामान्य चंद्र राशि आधारित.*)$", last, flags=re.S)
    if match:
        segments[-1] = (key, label, clean(last[: match.start()]))
        outro_text = clean(match.group(1))
    else:
        outro_text = (
            "यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है। "
            "व्यक्तिगत फलादेश के लिए जन्म कुंडली का अध्ययन आवश्यक होता है। "
            "वीडियो उपयोगी लगे तो लाइक, फॉलो और सब्सक्राइब करें। "
            "कल फिर मिलेंगे। नमस्कार!"
        )

    segments.append(("outro", "समापन", outro_text))

    if len(segments) != 14 or any(not item[2] for item in segments):
        raise RuntimeError("Expected 14 non-empty narration segments")

    return segments


def background():
    return Image.new("RGB", (W, H), (18, 5, 30)).convert("RGBA")


def put_hero(canvas, source, box):
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    source = ImageOps.exif_transpose(source.convert("RGB"))
    image = base.crop_cover(source, width, height)
    image = ImageEnhance.Color(image).enhance(1.12)
    image = ImageEnhance.Contrast(image).enhance(1.05)
    mask = Image.new("L", (width, height))
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, width - 1, height - 1), radius=40, fill=255
    )
    canvas.paste(image, (left, top), mask)


def intro(script):
    """Create one clean devotional opening image; never mirror the source."""
    output = SCENES / "000_intro.jpg"
    source = ImageOps.exif_transpose(Image.open(base.INTRO_ASSET).convert("RGB"))

    # Use one correctly oriented crop only. No mirrored duplicate is generated.
    crop = source.crop((0, 0, source.width, max(1, int(source.height * 0.52))))
    canvas = background()
    gold = (247, 202, 77, 255)
    cream = (255, 244, 214, 255)
    dark = (28, 5, 31, 240)

    hero = base.crop_cover(crop, W - 100, 1030)
    blurred = hero.filter(ImageFilter.GaussianBlur(26)).convert("RGBA")
    blurred.putalpha(105)
    canvas.alpha_composite(blurred, (50, 90))
    canvas.alpha_composite(hero.convert("RGBA"), (50, 90))

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 24, W - 24, H - 24), radius=42, outline=gold, width=4)

    title = "॥ दैनिक वैदिक ज्योतिष ॥"
    title_font = fit(draw, title, W - 120, 64, 40)
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((W - box[2] + box[0]) / 2, 1185), title, font=title_font, fill=cream)

    date = next(
        (line.strip() for line in script.splitlines() if line.strip().startswith("आज ")),
        "आज का दैनिक राशिफल",
    )
    date_font = fit(draw, date, W - 140, 38, 24)
    draw.rounded_rectangle((65, 1275, W - 65, 1360), radius=28, fill=dark, outline=gold, width=2)
    box = draw.textbbox((0, 0), date, font=date_font)
    draw.text(((W - box[2] + box[0]) / 2, 1298), date, font=date_font, fill=cream)

    transition = next(
        (line.strip() for line in script.splitlines() if "गोचर" in line or "प्रवेश" in line),
        "",
    )
    if transition:
        draw.rounded_rectangle((55, 1395, W - 55, 1615), radius=30, fill=dark, outline=gold, width=2)
        y = 1420
        for line in wrap("आज का प्रमुख गोचर : " + transition, 42)[:4]:
            line_font = fit(draw, line, W - 130, 30, 22)
            box = draw.textbbox((0, 0), line, font=line_font)
            draw.text(((W - box[2] + box[0]) / 2, y), line, font=line_font, fill=cream)
            y += 48

    hook = "ॐ  •  आस्था  •  ग्रह गोचर  •  शुभ संकेत  •  ॐ"
    hook_font = fit(draw, hook, W - 100, 30, 20)
    box = draw.textbbox((0, 0), hook, font=hook_font)
    draw.text(((W - box[2] + box[0]) / 2, 1660), hook, font=hook_font, fill=gold)

    subtitle = "बारहों राशियों के लिए आज के ग्रह संकेत"
    subtitle_font = fit(draw, subtitle, W - 100, 28, 20)
    box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((W - box[2] + box[0]) / 2, 1770), subtitle, font=subtitle_font, fill=cream)

    canvas.convert("RGB").save(output, "JPEG", quality=98, subsampling=0)
    return output


def rashi_scene(index, key, label, deity, image_path, narration):
    output = SCENES / f"{index:03d}_{key}.jpg"
    canvas = background()
    draw = ImageDraw.Draw(canvas)
    gold = (247, 202, 77, 255)
    cream = (255, 244, 214, 255)
    white = (255, 250, 242, 255)
    panel = (12, 4, 24, 242)

    draw.rounded_rectangle((24, 24, W - 24, H - 24), radius=42, outline=gold, width=4)
    draw.text((62, 62), "ॐ", font=font(56), fill=gold)
    label_font = fit(draw, label, W - 250, 62, 40)
    box = draw.textbbox((0, 0), label, font=label_font)
    draw.text(((W - box[2] + box[0]) / 2, 70), label, font=label_font, fill=cream)
    draw.text((W - 120, 62), "ॐ", font=font(56), fill=gold)

    put_hero(canvas, Image.open(image_path), (50, 180, W - 50, 1030))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((50, 180, W - 50, 1030), radius=40, outline=gold, width=4)

    # The deity's name is intentionally NOT printed below the photograph.
    draw.rounded_rectangle((50, 1090, W - 50, 1785), radius=32, fill=panel, outline=(208, 164, 62, 230), width=2)
    heading = "आज के ग्रह संकेत"
    heading_font = fit(draw, heading, W - 160, 34, 24)
    box = draw.textbbox((0, 0), heading, font=heading_font)
    draw.text(((W - box[2] + box[0]) / 2, 1130), heading, font=heading_font, fill=gold)

    body = re.sub(rf"^\s*{re.escape(key)}\s+राशि[।:\s]*", "", narration).strip()
    y = 1190
    for line in wrap(body, 38)[:15]:
        draw.text((90, y), line, font=font(29), fill=white)
        y += 39

    footer = "आज के लिए धैर्य • कर्म • विश्वास • सकारात्मक सोच"
    footer_font = fit(draw, footer, W - 120, 24, 18)
    box = draw.textbbox((0, 0), footer, font=footer_font)
    draw.text(((W - box[2] + box[0]) / 2, 1840), footer, font=footer_font, fill=gold)

    canvas.convert("RGB").save(output, "JPEG", quality=98, subsampling=0)
    return output


def outro():
    output = SCENES / "999_outro.jpg"
    canvas = background()
    draw = ImageDraw.Draw(canvas)
    gold = (247, 202, 77, 255)
    cream = (255, 244, 214, 255)
    draw.rounded_rectangle((24, 24, W - 24, H - 24), radius=42, outline=gold, width=4)
    draw.text((W // 2 - 55, 410), "ॐ", font=font(100), fill=gold)

    title = "॥ शुभम् भवतु ॥"
    title_font = fit(draw, title, W - 150, 64, 42)
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((W - box[2] + box[0]) / 2, 610), title, font=title_font, fill=cream)

    y = 800
    for line in [
        "आपका दिन शुभ और मंगलमय हो",
        "ईश्वर की कृपा और सकारात्मक ऊर्जा आपके साथ रहे",
        "कल फिर मिलेंगे नए ग्रह संकेतों के साथ",
    ]:
        line_font = fit(draw, line, W - 180, 34, 24)
        box = draw.textbbox((0, 0), line, font=line_font)
        draw.text(((W - box[2] + box[0]) / 2, y), line, font=line_font, fill=cream)
        y += 75

    canvas.convert("RGB").save(output, "JPEG", quality=98, subsampling=0)
    return output


def motion(ffmpeg, scene, seconds, index):
    """Render one scene for exactly `seconds`; never use a fixed scene length."""
    output = SCENES / f"motion_{index:02d}.mp4"
    frames = max(2, round(seconds * FPS))
    zoom = "min(1.13,1+0.00010*on)"
    if index % 2 == 0:
        x = f"(iw-iw/zoom)*(on/{frames})"
    else:
        x = f"(iw-iw/zoom)*(({frames}-on)/{frames})"
    y = "(ih-ih/zoom)/2"
    fade = min(0.28, max(0.10, seconds / 6))
    fade_out_start = max(0.05, seconds - fade)
    filtergraph = (
        f"zoompan=z={zoom}:x={x}:y={y}:d={frames}:s={W}x{H}:fps={FPS},"
        f"fade=t=in:st=0:d={fade:.3f},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade:.3f}"
    )
    run([
        ffmpeg, "-y", "-loop", "1", "-i", scene,
        "-vf", filtergraph,
        "-t", f"{seconds:.3f}",
        "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "19", "-pix_fmt", "yuv420p", output,
    ], 900)
    return output


def concat_video(ffmpeg, clips):
    output = SCENES / "video_no_audio_sync.mp4"
    args = [ffmpeg, "-y"]
    labels = []
    for index, clip in enumerate(clips):
        args += ["-i", clip]
        labels.append(f"[{index}:v]")
    args += [
        "-filter_complex",
        "".join(labels) + f"concat=n={len(clips)}:v=1:a=0[v]",
        "-map", "[v]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", output,
    ]
    run(args, 1800)
    return output


def concat_audio(ffmpeg, files):
    args = [ffmpeg, "-y"]
    labels = []
    for index, path in enumerate(files):
        args += ["-i", path]
        labels.append(f"[{index}:a]")
    args += [
        "-filter_complex",
        "".join(labels) + f"concat=n={len(files)}:v=0:a=1[a]",
        "-map", "[a]",
        "-c:a", "libmp3lame", "-b:a", "160k", VOICE,
    ]
    run(args, 1800)


def attach_audio(ffmpeg, silent_video, total):
    run([
        ffmpeg, "-y",
        "-i", silent_video,
        "-i", VOICE,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "160k",
        "-t", f"{total:.3f}",
        VIDEO,
    ], 1800)


def validate_assets():
    root = Path("assets/deities")
    result = {}
    for deity, filename in DEITIES.items():
        path = root / filename
        if not path.exists():
            raise RuntimeError(f"Missing deity artwork: {path}")
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            print(f"HD deity asset: {deity} -> {image.size}")
            if min(image.size) < 1200:
                raise RuntimeError(f"Deity artwork below 1200px: {path} -> {image.size}")
        result[deity] = path
    return result


def clean_outputs():
    OUT.mkdir(exist_ok=True)
    SCENES.mkdir(exist_ok=True)
    SEGDIR.mkdir(exist_ok=True)
    for path in list(SCENES.glob("*")) + list(SEGDIR.glob("*")):
        if path.is_file():
            path.unlink()
    for path in [VIDEO, VOICE, MANIFEST, OUT / "video_poster.png"]:
        if path.exists():
            path.unlink()


def main():
    clean_outputs()
    script = base.load_script()
    segments = split_script(script)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    deity_paths = validate_assets()

    audio_files = []
    durations = []
    manifest = []
    cursor = 0.0

    # Generate and measure every narration segment first. These durations become
    # the ONLY source of truth for the visual timeline.
    for index, (key, label, text) in enumerate(segments):
        path = SEGDIR / f"{index:02d}_{key}.mp3"
        print(f"TTS {index + 1}/14: {label}")
        asyncio.run(speak(text, path))
        seconds = media_duration(ffmpeg, path)
        audio_files.append(path)
        durations.append(seconds)
        manifest.append({
            "index": index,
            "key": key,
            "label": label,
            "start_seconds": round(cursor, 3),
            "end_seconds": round(cursor + seconds, 3),
            "audio_seconds": round(seconds, 3),
            "text": text,
        })
        cursor += seconds

    concat_audio(ffmpeg, audio_files)
    total_audio = media_duration(ffmpeg, VOICE)

    scenes = [intro(script)]
    for index, (key, label, deity, query) in enumerate(base.RASHIS, start=1):
        narration = next(item[2] for item in segments if item[0] == key)
        scenes.append(
            rashi_scene(
                index,
                key,
                label,
                deity,
                deity_paths[deity],
                narration,
            )
        )
    scenes.append(outro())

    if len(scenes) != len(segments):
        raise RuntimeError(f"Scene/voice count mismatch: {len(scenes)} vs {len(segments)}")

    clips = []
    for index, (scene, seconds) in enumerate(zip(scenes, durations)):
        manifest[index]["scene"] = str(scene)
        manifest[index]["scene_seconds"] = round(seconds, 3)
        clips.append(motion(ffmpeg, scene, seconds, index))

    silent_video = concat_video(ffmpeg, clips)
    attach_audio(ffmpeg, silent_video, total_audio)
    total_video = media_duration(ffmpeg, VIDEO)
    delta = abs(total_video - total_audio)
    print(
        f"{VERSION}: video={total_video:.3f}s "
        f"audio={total_audio:.3f}s delta={delta:.3f}s"
    )

    if delta > 0.20:
        raise RuntimeError("FINAL AUDIO/VIDEO SYNC FAILED")

    Image.open(scenes[0]).save(OUT / "video_poster.png", "PNG")
    MANIFEST.write_text(
        json.dumps(
            {
                "renderer": VERSION,
                "method": "audio-segment-duration-is-master-timeline",
                "transition": "fade-in/out inside each segment; zero overlap",
                "total_audio_seconds": round(total_audio, 3),
                "total_video_seconds": round(total_video, 3),
                "segments": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("PRODUCTION VIDEO COMPLETE")


if __name__ == "__main__":
    main()
