"""
Daily Astro Hindi - audio-led synchronized renderer.

The previous renderer generated ONE long narration and independently guessed
scene durations from text weights. That causes the narration to talk about
one section while the video has already moved to another Rashi.

This renderer fixes that architecture:
  1. Split daily_script.md into intro + 12 exact Rashi sections + outro.
  2. Generate a separate Hindi TTS audio segment for every section.
  3. Measure every segment's real duration.
  4. Give the corresponding visual scene exactly that audio duration plus
     the transition overlap.
  5. Concatenate the audio segments in the same order.
  6. Cross-fade visually at the exact audio section boundaries.

Result: the audio is the master timeline. A Rashi scene cannot appear before
its narration begins, and the next Rashi cannot appear while the previous
Rashi is still being narrated.
"""

from pathlib import Path
import asyncio
import json
import re
import subprocess

import edge_tts
import imageio_ffmpeg

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
FONT_PATH = base.FONT_PATH

TRANSITION = 0.6


async def synthesize(text: str, path: Path):
    communicate = edge_tts.Communicate(
        text,
        VOICE_NAME,
        rate="+5%",
        volume="+0%",
    )
    await communicate.save(str(path))


def clean_text(text: str) -> str:
    return " ".join(line.strip() for line in text.splitlines() if line.strip())


def split_script(script: str):
    """Split only on exact Rashi-heading lines; never on planet-name mentions."""
    lines = script.splitlines()
    starts = []

    for i, (key, label, deity, query) in enumerate(base.RASHIS):
        pattern = re.compile(rf"^\s*{re.escape(key)}\s+राशि(?:[।:]|\s)")
        for line_no, line in enumerate(lines):
            if pattern.search(line):
                starts.append((line_no, i, key, label, deity))
                break

    starts.sort(key=lambda x: x[0])

    if len(starts) != 12:
        found = [x[2] for x in starts]
        raise RuntimeError(
            f"Could not locate all 12 exact Rashi sections. Found: {found}"
        )

    # Require each Rashi exactly once and in the canonical order.
    indices = [x[1] for x in starts]
    if indices != list(range(12)):
        raise RuntimeError(
            "Rashi sections are not in canonical order: " + str(indices)
        )

    segments = []
    intro = clean_text("\n".join(lines[: starts[0][0]]))
    segments.append(("intro", "प्रस्तावना", intro))

    for pos, start in enumerate(starts):
        line_no, rashi_index, key, label, deity = start
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        body = clean_text("\n".join(lines[line_no:end]))
        segments.append((key, label, body))

    outro_start = starts[-1][0]
    last_end = len(lines)
    # Everything after the Mीन section's single/last line is outro content.
    # In today's script the Rashi is one line, but this also handles future
    # multiline Rashi sections by finding the end before outro markers.
    last_body = segments[-1][2]
    outro_markers = [
        "यह सामान्य चंद्र राशि आधारित",
        "वीडियो उपयोगी लगे",
    ]
    marker_positions = [script.find(m) for m in outro_markers if script.find(m) >= 0]
    if marker_positions:
        marker_pos = min(marker_positions)
        outro = clean_text(script[marker_pos:])
        # Remove the same outro from the final Rashi segment.
        last_start_text = script.find(f"{starts[-1][2]} राशि")
        if last_start_text >= 0:
            new_last = clean_text(script[last_start_text:marker_pos])
            segments[-1] = (segments[-1][0], segments[-1][1], new_last)
    else:
        outro = ""

    if not outro:
        outro = "नमस्कार। कल फिर मिलेंगे नए ग्रह संकेतों के साथ।"

    segments.append(("outro", "समापन", outro))
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
    """Concatenate TTS segments into the public daily_voice.mp3."""
    inputs = []
    labels = []
    for i, path in enumerate(audio_files):
        inputs += ["-i", str(path)]
        labels.append(f"[{i}:a]")

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


def make_clip(ffmpeg, scene, duration, index):
    """Make a motion clip. Duration includes transition overlap."""
    return base.make_animated_clip(ffmpeg, scene, duration, index)


def render_video(ffmpeg, scenes, audio_durations):
    """
    Audio durations are authoritative.

    Each visual clip gets audio_duration + TRANSITION. The xfade starts at the
    exact cumulative audio boundary, so the next visual begins transitioning
    precisely when the next narration segment begins.
    """
    durations = [d + TRANSITION for d in audio_durations]

    if len(scenes) != len(durations):
        raise RuntimeError(
            f"Scene/audio mismatch: {len(scenes)} scenes vs {len(durations)} audio segments"
        )

    clips = []
    for i, (scene, clip_duration) in enumerate(zip(scenes, durations)):
        clips.append(make_clip(ffmpeg, scene, clip_duration, i))

    inputs = []
    for clip in clips:
        inputs += ["-i", str(clip)]

    filters = []
    current = "[0:v]"
    elapsed = durations[0]

    for i in range(1, len(clips)):
        # Because each clip includes TRANSITION extra seconds, this offset is
        # exactly the cumulative duration of preceding audio segments.
        offset = elapsed - TRANSITION
        label = f"[xf{i}]"
        filters.append(
            f"{current}[{i}:v]"
            f"xfade=transition=fade:duration={TRANSITION}:offset={offset:.3f}"
            f"{label}"
        )
        current = label
        elapsed += durations[i] - TRANSITION

    silent = SCENES / "video_no_audio_sync.mp4"
    filtergraph = ";".join(filters)

    subprocess.run(
        [
            ffmpeg, "-y", *inputs,
            "-filter_complex", filtergraph,
            "-map", current,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-an", str(silent),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=1800,
    )

    # Audio is authoritative. -shortest trims the extra TRANSITION padding at
    # the very end, without changing any section boundary.
    subprocess.run(
        [
            ffmpeg, "-y",
            "-i", str(silent),
            "-i", str(VOICE),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            str(VIDEO),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=1800,
    )


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    SCENES.mkdir(parents=True, exist_ok=True)
    SYNC_DIR.mkdir(parents=True, exist_ok=True)

    script = base.load_script()
    print("Loaded daily_script.md")

    segments = split_script(script)
    print(f"Detected {len(segments)} synchronized narration segments.")

    # Clear only generated segment audio.
    for p in SYNC_DIR.glob("*.mp3"):
        p.unlink()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    audio_files = []
    audio_durations = []
    manifest_segments = []

    for index, (key, label, text) in enumerate(segments):
        if not text:
            raise RuntimeError(f"Empty narration segment: {key}")
        path = SYNC_DIR / f"{index:02d}_{key}.mp3"
        print(f"Generating TTS: {label}")
        asyncio.run(synthesize(text, path))
        d = duration(ffmpeg, path)
        audio_files.append(path)
        audio_durations.append(d)
        manifest_segments.append({
            "index": index,
            "key": key,
            "label": label,
            "audio_seconds": round(d, 3),
            "scene": None,
            "text": text,
        })

    concat_audio(ffmpeg, audio_files)

    deity_paths = base.prepare_deities()

    scenes = []
    intro_scene = base.create_intro(script)
    scenes.append(intro_scene)

    # Exact same canonical order used by split_script().
    for index, (key, label, deity, query) in enumerate(base.RASHIS, start=1):
        text = next(seg[2] for seg in segments if seg[0] == key)
        scene = base.create_scene(
            index,
            key,
            label,
            deity,
            deity_paths[deity],
            text,
        )
        scenes.append(scene)

    scenes.append(base.create_outro())

    if len(scenes) != len(audio_durations):
        raise RuntimeError(
            f"Internal sync error: {len(scenes)} scenes for {len(audio_durations)} audio segments"
        )

    for item, scene in zip(manifest_segments, scenes):
        item["scene"] = str(scene)

    render_video(ffmpeg, scenes, audio_durations)

    manifest = {
        "method": "audio-led-section-sync-v1",
        "transition_seconds": TRANSITION,
        "segments": manifest_segments,
        "total_audio_seconds": round(sum(audio_durations), 3),
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # The poster is always the actual intro frame.
    poster = OUTPUT / "video_poster.png"
    base.create_intro(script).save(poster, "PNG")

    print("========================================")
    print("AUDIO-LED SYNCHRONIZED VIDEO COMPLETE")
    print("========================================")
    print(f"VIDEO:    {VIDEO}")
    print(f"VOICE:    {VOICE}")
    print(f"MANIFEST: {MANIFEST}")
    print(f"Segments: {len(segments)}")
    print(f"Duration: {sum(audio_durations):.2f}s")
    print("Sync: each Rashi scene is timed from its own TTS audio segment.")


if __name__ == "__main__":
    main()
