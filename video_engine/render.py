"""
Daily Hindi Vedic Astrology Video Renderer

Creates:
    output/daily_video.mp4
    output/daily_voice.mp3
    output/daily_subtitles.ass

Pipeline:
    daily_script.md
        ↓
    Hindi TTS
        ↓
    Timed subtitles
        ↓
    Vertical 1080x1920 video
        ↓
    MP4 with narration + subtitles
"""

from pathlib import Path
import asyncio
import subprocess
import re
import shutil

import edge_tts


# ============================================================
# PATHS
# ============================================================

OUTPUT_DIR = Path("output")

SCRIPT_FILE = OUTPUT_DIR / "daily_script.md"

VOICE_FILE = OUTPUT_DIR / "daily_voice.mp3"

ASS_FILE = OUTPUT_DIR / "daily_subtitles.ass"

VIDEO_FILE = OUTPUT_DIR / "daily_video.mp4"

TEMP_DIR = OUTPUT_DIR / "video_temp"


# ============================================================
# VOICE
# ============================================================

VOICE = "hi-IN-SwaraNeural"

VOICE_RATE = "+8%"

VOICE_VOLUME = "+0%"


# ============================================================
# VIDEO
# ============================================================

WIDTH = 1080

HEIGHT = 1920

FPS = 30


# ============================================================
# COLORS
# ============================================================

BACKGROUND = "&H00130B2B"

WHITE = "&H00FFFFFF"

GOLD = "&H0000D7FF"

LIGHT = "&H00E8E2F5"


# ============================================================
# HELPERS
# ============================================================

def run_command(command):

    print(
        "RUN:",
        " ".join(
            str(x)
            for x in command
        )
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(result.stdout)

    if result.returncode != 0:

        raise RuntimeError(
            "Command failed with exit code "
            f"{result.returncode}"
        )


def check_command(name):

    if shutil.which(name) is None:

        raise RuntimeError(
            f"Required command not found: {name}"
        )


def clean_line(text):

    text = text.strip()

    text = re.sub(
        r"^#+\s*",
        "",
        text
    )

    return text


def load_script():

    if not SCRIPT_FILE.exists():

        raise SystemExit(
            "Run the astrology pipeline first."
        )

    raw = SCRIPT_FILE.read_text(
        encoding="utf-8"
    )

    lines = []

    for line in raw.splitlines():

        line = clean_line(
            line
        )

        if not line:
            continue

        lines.append(
            line
        )

    if not lines:

        raise RuntimeError(
            "daily_script.md is empty."
        )

    return lines


# ============================================================
# TTS
# ============================================================

async def generate_tts():

    text_lines = load_script()

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    audio_files = []

    print(
        f"Generating Hindi narration for "
        f"{len(text_lines)} sections..."
    )

    for index, text in enumerate(
        text_lines,
        start=1
    ):

        output_file = (
            TEMP_DIR
            / f"voice_{index:03d}.mp3"
        )

        print(
            f"TTS {index}/{len(text_lines)}"
        )

        communicate = edge_tts.Communicate(
            text,
            VOICE,
            rate=VOICE_RATE,
            volume=VOICE_VOLUME,
        )

        await communicate.save(
            str(output_file)
        )

        audio_files.append(
            output_file
        )

    concat_file = (
        TEMP_DIR
        / "audio_concat.txt"
    )

    with concat_file.open(
        "w",
        encoding="utf-8"
    ) as f:

        for audio in audio_files:

            escaped = str(
                audio.resolve()
            ).replace(
                "'",
                "'\\''"
            )

            f.write(
                f"file '{escaped}'\n"
            )

    run_command([
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(VOICE_FILE),
    ])

    return text_lines


# ============================================================
# AUDIO DURATIONS
# ============================================================

def get_duration(path):

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr
        )

    return float(
        result.stdout.strip()
    )


# ============================================================
# ASS HELPERS
# ============================================================

def ass_time(seconds):

    hours = int(
        seconds // 3600
    )

    minutes = int(
        (seconds % 3600) // 60
    )

    secs = seconds % 60

    whole = int(
        secs
    )

    centiseconds = int(
        round(
            (secs - whole) * 100
        )
    )

    if centiseconds >= 100:

        whole += 1

        centiseconds = 0

    return (
        f"{hours}:"
        f"{minutes:02d}:"
        f"{whole:02d}."
        f"{centiseconds:02d}"
    )


def ass_escape(text):

    text = text.replace(
        "\\",
        r"\\"
    )

    text = text.replace(
        "{",
        r"\{"
    )

    text = text.replace(
        "}",
        r"\}"
    )

    return text


# ============================================================
# CREATE SUBTITLES
# ============================================================

def create_ass_subtitles(
    lines
):

    durations = []

    for index in range(
        1,
        len(lines) + 1
    ):

        audio_file = (
            TEMP_DIR
            / f"voice_{index:03d}.mp3"
        )

        durations.append(
            get_duration(
                audio_file
            )
        )

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Noto Sans Devanagari,70,&H0000D7FF,&H0000D7FF,&H00130B2B,&H80130B2B,1,0,0,0,100,100,0,0,1,4,2,8,70,70,150,1
Style: Body,Noto Sans Devanagari,48,&H00FFFFFF,&H00FFFFFF,&H00130B2B,&H80130B2B,0,0,0,0,100,100,0,0,1,3,2,5,80,80,260,1
Style: Footer,Noto Sans Devanagari,32,&H00E8E2F5,&H00E8E2F5,&H00130B2B,&H80130B2B,0,0,0,0,100,100,0,0,1,2,1,2,70,70,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []

    current = 0.0

    for index, (
        text,
        duration
    ) in enumerate(
        zip(
            lines,
            durations
        )
    ):

        start = current

        end = current + duration

        safe = ass_escape(
            text
        )

        # First line is the main title.
        if index == 0:

            style = "Title"

        else:

            style = "Body"

        events.append(
            "Dialogue: "
            f"0,"
            f"{ass_time(start)},"
            f"{ass_time(end)},"
            f"{style},,"
            f"0,0,0,,"
            f"{safe}"
        )

        current = end

    # Permanent footer.
    total = current

    events.append(
        "Dialogue: "
        f"0,"
        f"{ass_time(0)},"
        f"{ass_time(total)},"
        f"Footer,,"
        f"0,0,0,,"
        r"दैनिक वैदिक ज्योतिष • सामान्य गोचर विश्लेषण"
    )

    ASS_FILE.write_text(
        header
        + "\n".join(events)
        + "\n",
        encoding="utf-8"
    )

    return total


# ============================================================
# VIDEO
# ============================================================

def render_video(
    duration
):

    # Use a clean vertical background.
    video_source = (
        "color="
        f"c={BACKGROUND}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"r={FPS}"
    )

    run_command([
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        video_source,
        "-i",
        str(VOICE_FILE),
        "-vf",
        f"subtitles={ASS_FILE}:"
        "fontsdir=/usr/share/fonts/truetype/noto",
        "-t",
        f"{duration:.3f}",
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        str(VIDEO_FILE),
    ])


# ============================================================
# MAIN
# ============================================================

def render():

    check_command(
        "ffmpeg"
    )

    check_command(
        "ffprobe"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    lines = asyncio.run(
        generate_tts()
    )

    duration = create_ass_subtitles(
        lines
    )

    render_video(
        duration
    )

    print()
    print(
        "========================================"
    )
    print(
        "VIDEO GENERATION COMPLETE"
    )
    print(
        "========================================"
    )

    print(
        f"Script:     {SCRIPT_FILE}"
    )

    print(
        f"Voice:      {VOICE_FILE}"
    )

    print(
        f"Subtitles:  {ASS_FILE}"
    )

    print(
        f"Video:      {VIDEO_FILE}"
    )

    print(
        f"Duration:   {duration:.1f} seconds"
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    render()
