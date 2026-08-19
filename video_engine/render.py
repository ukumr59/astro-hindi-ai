"""
Automated Hindi Vedic Astrology Video Renderer

Uses:
- edge-tts for Hindi narration
- imageio-ffmpeg for a self-contained FFmpeg binary
- Pillow for video artwork

No apt-get.
No system FFmpeg dependency.
No system espeak dependency.
"""

from pathlib import Path
import asyncio
import subprocess
import textwrap
import urllib.request

from PIL import Image, ImageDraw, ImageFont
import edge_tts
import imageio_ffmpeg


OUTPUT = Path("output")

SCRIPT = OUTPUT / "daily_script.md"
VOICE = OUTPUT / "daily_voice.mp3"
VIDEO = OUTPUT / "daily_video.mp4"
POSTER = OUTPUT / "video_poster.png"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

VOICE_NAME = "hi-IN-SwaraNeural"


# ------------------------------------------------------------
# FONTS
# ------------------------------------------------------------

FONT_URL = (
    "https://github.com/googlefonts/"
    "noto-fonts/raw/main/hinted/ttf/"
    "NotoSansDevanagari/"
    "NotoSansDevanagari-Regular.ttf"
)

FONT_PATH = OUTPUT / "NotoSansDevanagari-Regular.ttf"


def get_font(size):

    if not FONT_PATH.exists():

        print("Downloading Devanagari font...")

        urllib.request.urlretrieve(
            FONT_URL,
            FONT_PATH
        )

    return ImageFont.truetype(
        str(FONT_PATH),
        size
    )


# ------------------------------------------------------------
# COMMAND EXECUTION
# ------------------------------------------------------------

def run(command):

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
        timeout=600
    )

    print(result.stdout)

    if result.returncode != 0:

        raise RuntimeError(
            "Command failed with exit code "
            f"{result.returncode}"
        )


# ------------------------------------------------------------
# SCRIPT
# ------------------------------------------------------------

def read_script():

    if not SCRIPT.exists():

        raise RuntimeError(
            "output/daily_script.md was not generated."
        )

    text = SCRIPT.read_text(
        encoding="utf-8"
    ).strip()

    if not text:

        raise RuntimeError(
            "daily_script.md is empty."
        )

    return text


# ------------------------------------------------------------
# HINDI TTS
# ------------------------------------------------------------

async def create_voice(text):

    print(
        "Generating Hindi narration..."
    )

    communicate = edge_tts.Communicate(
        text,
        VOICE_NAME,
        rate="+5%",
        volume="+0%"
    )

    await communicate.save(
        str(VOICE)
    )

    if not VOICE.exists():

        raise RuntimeError(
            "Hindi voice file was not created."
        )


# ------------------------------------------------------------
# AUDIO DURATION
# ------------------------------------------------------------

def get_duration(ffmpeg):

    result = subprocess.run(
        [
            ffmpeg,
            "-i",
            str(VOICE)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30
    )

    output = result.stderr

    marker = "Duration:"

    if marker not in output:

        raise RuntimeError(
            "Unable to determine audio duration."
        )

    value = output.split(
        marker,
        1
    )[1].split(
        ",",
        1
    )[0].strip()

    hours, minutes, seconds = value.split(":")

    return (
        int(hours) * 3600
        + int(minutes) * 60
        + float(seconds)
    )


# ------------------------------------------------------------
# POSTER
# ------------------------------------------------------------

def create_poster(text):

    print(
        "Creating Hindi video artwork..."
    )

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (19, 11, 43)
    )

    draw = ImageDraw.Draw(
        image
    )

    title_font = get_font(
        70
    )

    body_font = get_font(
        44
    )

    small_font = get_font(
        32
    )

    title = "दैनिक वैदिक ज्योतिष"

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=title_font
    )

    title_width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (WIDTH - title_width) / 2,
            120
        ),
        title,
        font=title_font,
        fill=(255, 215, 80)
    )

    # Take useful lines from generated script.
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    display_text = "\n\n".join(
        lines[:14]
    )

    wrapped = []

    for paragraph in display_text.split(
        "\n"
    ):

        wrapped.extend(
            textwrap.wrap(
                paragraph,
                width=25
            )
        )

    y = 330

    for line in wrapped[:24]:

        draw.text(
            (
                80,
                y
            ),
            line,
            font=body_font,
            fill=(255, 255, 255)
        )

        y += 65

        if y > 1600:
            break

    footer = (
        "दैनिक चंद्र राशि आधारित गोचर विश्लेषण"
    )

    bbox = draw.textbbox(
        (0, 0),
        footer,
        font=small_font
    )

    footer_width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (WIDTH - footer_width) / 2,
            1800
        ),
        footer,
        font=small_font,
        fill=(220, 215, 235)
    )

    image.save(
        POSTER,
        quality=95
    )


# ------------------------------------------------------------
# VIDEO
# ------------------------------------------------------------

def create_video():

    print(
        "Loading bundled FFmpeg..."
    )

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    print(
        f"FFmpeg: {ffmpeg}"
    )

    duration = get_duration(
        ffmpeg
    )

    print(
        f"Audio duration: {duration:.1f}s"
    )

    # Generate a video from the poster image.
    run([
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(POSTER),
        "-i",
        str(VOICE),
        "-t",
        f"{duration:.2f}",
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
        str(VIDEO)
    ])

    if not VIDEO.exists():

        raise RuntimeError(
            "daily_video.mp4 was not created."
        )


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    text = read_script()

    print(
        "Script loaded successfully."
    )

    asyncio.run(
        create_voice(text)
    )

    create_poster(
        text
    )

    create_video()

    print()
    print(
        "======================================"
    )
    print(
        "VIDEO GENERATION COMPLETE"
    )
    print(
        "======================================"
    )
    print(
        f"Script : {SCRIPT}"
    )
    print(
        f"Voice  : {VOICE}"
    )
    print(
        f"Poster : {POSTER}"
    )
    print(
        f"Video  : {VIDEO}"
    )
    print(
        "======================================"
    )


if __name__ == "__main__":
    main()
