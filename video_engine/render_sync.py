"""
Daily Astro Hindi - production audio-led synchronized renderer.

The narration is the master timeline. Every visual scene is rendered for the
real duration of its own TTS segment. Scenes are concatenated without overlap,
so the next Rashi can NEVER appear before its narration starts.

Also fixes the previous intro duplication/reflection problem by using the
intro artwork once as a full-screen hero rather than repeating the same source
image in two vertical regions.
"""

from pathlib import Path
import asyncio
import json
import re
import subprocess

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

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

FADE_SECONDS = 0.28


async def synthesize(text: str, path: Path):
    communicate = edge_tts.Communicate(
        text,
        VOICE_NAME,
        rate="+5%",
        volume="+0%",
    )
    await communicate.save(str(path))


def clean_text(text: str) -> str:
    return " ".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    )


def split_script(script: str):
    """
    Split the generated script into exactly:
      intro + 12 Rashi sections + outro.

    The content engine emits each Rashi as a line beginning with
    '<राशि> राशि।'. We use that exact structure rather than text-length
    estimates or searches for planet names.
    """
    lines = script.splitlines()
    starts = []

    for rashi_index, (key, label, deity, query) in enumerate(base.RASHIS):
        pattern = re.compile(
            rf"^\s*{re.escape(key)}\s+राशि(?:[।:]|\s)"
        )
        matches = [
            line_no
            for line_no, line in enumerate(lines)
            if pattern.search(line)
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected exactly one heading for {key} राशि; found {len(matches)}."
            )
        starts.append((matches[0], rashi_index, key, label, deity))

    starts.sort(key=lambda item: item[0])

    if [x[1] for x in starts] != list(range(12)):
        raise RuntimeError("Rashi sections are not in canonical order.")

    intro = clean_text("\n".join(lines[: starts[0][0]]))
    segments = [("intro", "प्रस्तावना", intro)]

    for pos, (line_no, rashi_index, key, label, deity) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        body = clean_text("\n".join(lines[line_no:end]))
        segments.append((key, label, body))

    last_key, last_label, last_body = segments[-1]
    marker = re.search(
        r"(यह सामान्य चंद्र राशि आधारित.*)$",
        last_body,
        flags=re.DOTALL,
    )

    if marker:
        meeen_body = clean_text(last_body[: marker.start()])
        outro = clean_text(marker.group(1))
        segments[-1] = (last_key, last_label, meeen_body)
    else:
        outro = (
            "यह सामान्य चंद्र राशि आधारित वैदिक गोचर विश्लेषण है; "
            "व्यक्तिगत फलादेश के लिए जन्म कुंडली और दशा का अध्ययन आवश्यक होता है। "
            "वीडियो उपयोगी लगे तो लाइक, फॉलो और सब्सक्राइब करें। "
            "कल फिर मिलेंगे नए ग्रह संकेतों के साथ। नमस्कार!"
        )

    if not intro:
        raise RuntimeError("Intro narration is empty.")
    if not outro:
        raise RuntimeError("Outro narration is empty.")

    segments.append(("outro", "समापन", outro))

    if len(segments) != 14:
        raise RuntimeError(f"Expected 14 narration segments, got {len(segments)}.")

    return segments


def duration(ffmpeg, path: Path) -> float:
    result = subprocess.run(
        [ffmpeg, "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    match = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
        result.stderr,
    )
    if not match:
        raise RuntimeError(f"Could not determine duration for {path}")
    return (
        int(match.group(1)) * 3600
        + int(match.group(2)) * 60
        + float(match.group(3))
    )


def concat_audio(ffmpeg, audio_files):
    """Build daily_voice.mp3 from the exact same 14 segments used by video."""
    inputs = []
    labels = []
    for index, path in enumerate(audio_files):
        inputs.extend(["-i", str(path)])
        labels.append(f"[{index}:a]")

    filtergraph = "".join(labels) + f"concat=n={len(audio_files)}:v=0:a=1[a]"

    subprocess.run(
        [
            ffmpeg, "-y", *inputs,
            "-filter_complex", filtergraph,
            "-map", "[a]",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            str(VOICE),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=1800,
    )


def create_intro_fixed(script_text):
    """Use the intro artwork exactly once, full-screen; never duplicate it."""
    output = SCENES / "000_intro.jpg"

    if not base.INTRO_ASSET.exists():
        raise RuntimeError(f"Missing opening artwork: {base.INTRO_ASSET}")

    source = ImageOps.exif_transpose(
        Image.open(base.INTRO_ASSET).convert("RGB")
    )
    canvas = base.crop_cover(source, WIDTH, HEIGHT)
    canvas = ImageEnhance.Contrast(canvas).enhance(1.08)
    canvas = ImageEnhance.Color(canvas).enhance(1.06)

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (8, 2, 20, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(HEIGHT):
        if y < HEIGHT * 0.52:
            alpha = 18
        else:
            alpha = int(18 + 155 * ((y - HEIGHT * 0.52) / (HEIGHT * 0.48)))
        od.line((0, y, WIDTH, y), fill=(8, 2, 20, min(175, alpha)))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(canvas)

    gold = (255, 215, 80, 255)
    cream = (255, 246, 218, 255)
    deep = (35, 5, 24, 220)

    date_line = next(
        (line.strip() for line in script_text.splitlines() if line.strip().startswith("आज ")),
        "आज का दैनिक वैदिक ज्योतिष अपडेट",
    )
    transition_line = next(
        (
            line.strip()
            for line in script_text.splitlines()
            if "प्रमुख ग्रह परिवर्तन" not in line
            and ("राशि में प्रवेश" in line or "गोचर" in line)
        ),
        "",
    )

    title_font = base.get_font(78)
    subtitle_font = base.get_font(42)
    small_font = base.get_font(31)

    title = "॥ दैनिक वैदिक ज्योतिष ॥"
    tb = draw.textbbox((0, 0), title, font=title_font)
    draw.rounded_rectangle((45, 90, WIDTH - 45, 235), radius=38, fill=deep, outline=gold, width=4)
    draw.text(((WIDTH - (tb[2] - tb[0])) / 2, 112), title, font=title_font, fill=cream)

    db = draw.textbbox((0, 0), date_line, font=subtitle_font)
    draw.rounded_rectangle((70, 1300, WIDTH - 70, 1395), radius=28, fill=deep, outline=gold, width=3)
    draw.text(((WIDTH - (db[2] - db[0])) / 2, 1322), date_line, font=subtitle_font, fill=cream)

    hook = "ॐ  •  आस्था  •  ज्योतिष  •  शुभ ऊर्जा  •  ॐ"
    hb = draw.textbbox((0, 0), hook, font=subtitle_font)
    draw.text(((WIDTH - (hb[2] - hb[0])) / 2, 1455), hook, font=subtitle_font, fill=gold)

    if transition_line:
        transition = "आज का प्रमुख गोचर : " + transition_line
        tf = base.get_font(30)
        trb = draw.textbbox((0, 0), transition, font=tf)
        if trb[2] - trb[0] <= WIDTH - 90:
            draw.rounded_rectangle((45, 1550, WIDTH - 45, 1640), radius=25, fill=(12, 3, 22, 220), outline=(255, 205, 70, 210), width=2)
            draw.text(((WIDTH - (trb[2] - trb[0])) / 2, 1573), transition, font=tf, fill=cream)

    footer = "बारहों राशियों के लिए आज के ग्रह संकेत"
    fb = draw.textbbox((0, 0), footer, font=small_font)
    draw.text(((WIDTH - (fb[2] - fb[0])) / 2, 1770), footer, font=small_font, fill=cream)

    draw.rectangle((0, 0, WIDTH, 9), fill=gold)
    draw.rectangle((0, HEIGHT - 9, WIDTH, HEIGHT), fill=gold)

    canvas.convert("RGB").save(output, "JPEG", quality=96, subsampling=0)
    return output


def make_motion_clip(ffmpeg, scene, duration_seconds, index):
    """
    Animate one still image for exactly its narration duration.
    Fade-in/out is contained inside the segment; there is NO overlap between
    consecutive Rashi scenes.
    """
    output = SCENES / f"clip_sync_{index:02d}.mp4"
    frames = max(1, int(round(duration_seconds * FPS)))
    zoom_expr = "min(1.12,1+0.00012*on)"

    if index % 2:
        x_expr = "(iw-iw/zoom)*on/max(1,%d)" % frames
    else:
        x_expr = "(iw-iw/zoom)*(1-on/max(1,%d))" % frames
    y_expr = "(ih-ih/zoom)/2"

    fade_in = min(FADE_SECONDS, max(0.05, duration_seconds / 4))
    fade_out_start = max(0.0, duration_seconds - fade_in)
    vf = (
        "zoompan="
        f"z={zoom_expr}:x={x_expr}:y={y_expr}:d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"fade=t=in:st=0:d={fade_in:.3f},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade_in:.3f}"
    )

    subprocess.run(
        [
            ffmpeg, "-y", "-loop", "1", "-i", str(scene),
            "-vf", vf, "-t", f"{duration_seconds:.3f}", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", str(output),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=900,
    )
    return output


def concatenate_video(ffmpeg, clips):
    """Concatenate exact-duration clips with no overlap."""
    inputs = []
    labels = []
    for index, clip in enumerate(clips):
        inputs.extend(["-i", str(clip)])
        labels.append(f"[{index}:v]")

    filtergraph = "".join(labels) + f"concat=n={len(clips)}:v=1:a=0[v]"
    output = SCENES / "video_no_audio_sync.mp4"

    subprocess.run(
        [
            ffmpeg, "-y", *inputs,
            "-filter_complex", filtergraph,
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", str(output),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=1800,
    )
    return output


def attach_audio(ffmpeg, silent_video, total_seconds):
    subprocess.run(
        [
            ffmpeg, "-y",
            "-i", str(silent_video),
            "-i", str(VOICE),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-t", f"{total_seconds:.3f}",
            str(VIDEO),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=1800,
    )


def validate_output(ffmpeg, audio_seconds, scene_seconds):
    result = subprocess.run(
        [ffmpeg, "-i", str(VIDEO)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError("Could not determine final video duration.")

    video_seconds = (
        int(match.group(1)) * 3600
        + int(match.group(2)) * 60
        + float(match.group(3))
    )
    delta = abs(video_seconds - audio_seconds)
    print(f"Final duration check: video={video_seconds:.3f}s audio={audio_seconds:.3f}s delta={delta:.3f}s")

    if delta > 0.20:
        raise RuntimeError("Audio/video duration mismatch exceeds 0.20 seconds.")
    if any(x <= 0 for x in scene_seconds):
        raise RuntimeError("One or more synchronized scene durations is zero.")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    SCENES.mkdir(parents=True, exist_ok=True)
    SYNC_DIR.mkdir(parents=True, exist_ok=True)

    script = base.load_script()
    print("Loaded daily_script.md")

    segments = split_script(script)
    print(f"Detected {len(segments)} synchronized narration segments.")

    for path in SYNC_DIR.glob("*.mp3"):
        path.unlink()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    audio_files = []
    audio_durations = []
    manifest_segments = []

    for index, (key, label, text) in enumerate(segments):
        if not text:
            raise RuntimeError(f"Empty narration segment: {key}")
        path = SYNC_DIR / f"{index:02d}_{key}.mp3"
        print(f"Generating TTS segment {index + 1}/14: {label}")
        asyncio.run(synthesize(text, path))
        seconds = duration(ffmpeg, path)
        audio_files.append(path)
        audio_durations.append(seconds)
        manifest_segments.append({
            "index": index,
            "key": key,
            "label": label,
            "audio_seconds": round(seconds, 3),
            "scene_seconds": round(seconds, 3),
            "scene": None,
            "text": text,
        })
        print(f"  {label}: {seconds:.3f}s")

    concat_audio(ffmpeg, audio_files)
    # The concatenated public MP3 is the final audio master. Measure it after
    # concatenation so encoder padding cannot create a hidden duration drift.
    audio_duration_total = duration(ffmpeg, VOICE)

    deity_paths = base.prepare_deities()
    scenes = [create_intro_fixed(script)]

    for index, (key, label, deity, query) in enumerate(base.RASHIS, start=1):
        text = next(segment[2] for segment in segments if segment[0] == key)
        scenes.append(base.create_scene(index, key, label, deity, deity_paths[deity], text))

    scenes.append(base.create_outro())

    if len(scenes) != len(audio_durations):
        raise RuntimeError(f"Internal sync error: {len(scenes)} scenes vs {len(audio_durations)} audio segments.")

    for item, scene in zip(manifest_segments, scenes):
        item["scene"] = str(scene)

    clips = []
    for index, (scene, seconds) in enumerate(zip(scenes, audio_durations)):
        print(f"Rendering synchronized scene {index + 1}/14: {seconds:.3f}s")
        clips.append(make_motion_clip(ffmpeg, scene, seconds, index))

    silent = concatenate_video(ffmpeg, clips)
    attach_audio(ffmpeg, silent, audio_duration_total)
    validate_output(ffmpeg, audio_duration_total, audio_durations)

    Image.open(scenes[0]).save(OUTPUT / "video_poster.png", "PNG")

    manifest = {
        "method": "audio-led-exact-boundary-v2",
        "transition_seconds": FADE_SECONDS,
        "transition_type": "contained_fade_no_overlap",
        "total_audio_seconds": round(audio_duration_total, 3),
        "segments": manifest_segments,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========================================")
    print("AUDIO-LED SYNCHRONIZED VIDEO COMPLETE")
    print("========================================")
    print(f"VIDEO:    {VIDEO}")
    print(f"VOICE:    {VOICE}")
    print(f"MANIFEST: {MANIFEST}")
    print(f"Duration: {audio_duration_total:.2f}s")
    print("Sync: each Rashi scene has exactly the duration of its own narration segment; transitions never overlap into the next segment.")


if __name__ == "__main__":
    main()
