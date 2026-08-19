from pathlib import Path
import asyncio
import subprocess
import shutil
import edge_tts


OUTPUT = Path("output")
SCRIPT = OUTPUT / "daily_script.md"
VOICE = OUTPUT / "daily_voice.mp3"
VIDEO = OUTPUT / "daily_video.mp4"


VOICE_NAME = "hi-IN-SwaraNeural"


def run(cmd):
    print("RUN:", " ".join(str(x) for x in cmd))

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {result.returncode}"
        )


async def make_voice(text):

    communicate = edge_tts.Communicate(
        text,
        VOICE_NAME,
        rate="+5%",
    )

    await communicate.save(
        str(VOICE)
    )


def duration():

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(VOICE),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return float(
        result.stdout.strip()
    )


def make_video():

    seconds = duration()

    filter_text = (
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/"
        "noto/NotoSansDevanagari-Regular.ttf:"
        "text='दैनिक वैदिक ज्योतिष':"
        "fontcolor=white:"
        "fontsize=64:"
        "x=(w-text_w)/2:"
        "y=120:"
        "box=1:"
        "boxcolor=black@0.45:"
        "boxborderw=20"
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x130B2B:"
            "s=1080x1920:"
            "r=30",
            "-i",
            str(VOICE),
            "-vf",
            filter_text,
            "-t",
            str(seconds),
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
            str(VIDEO),
        ]
    )


def render():

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    if not SCRIPT.exists():
        raise SystemExit(
            "daily_script.md not found."
        )

    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "FFmpeg is not installed."
        )

    if shutil.which("ffprobe") is None:
        raise SystemExit(
            "FFprobe is not installed."
        )

    text = SCRIPT.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        raise SystemExit(
            "daily_script.md is empty."
        )

    print(
        "Generating ONE Hindi narration file..."
    )

    asyncio.run(
        make_voice(text)
    )

    print(
        "Generating video..."
    )

    make_video()

    print()
    print(
        "================================"
    )
    print(
        "VIDEO GENERATION COMPLETE"
    )
    print(
        f"Voice: {VOICE}"
    )
    print(
        f"Video: {VIDEO}"
    )
    print(
        "================================"
    )


if __name__ == "__main__":
    render()
