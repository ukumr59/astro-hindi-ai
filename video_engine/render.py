from pathlib import Path
import subprocess
import shutil


OUTPUT = Path("output")

SCRIPT = OUTPUT / "daily_script.md"
AUDIO = OUTPUT / "daily_voice.wav"
VIDEO = OUTPUT / "daily_video.mp4"


WIDTH = 1080
HEIGHT = 1920
FPS = 30


def run(command):
    print("RUN:", " ".join(str(x) for x in command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}"
        )


def require(command):
    if shutil.which(command) is None:
        raise RuntimeError(
            f"{command} is not installed."
        )


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


def create_voice(text):

    print("Generating local Hindi narration...")

    # espeak-ng has no network dependency.
    run([
        "espeak-ng",
        "-v",
        "hi",
        "-s",
        "145",
        "-p",
        "45",
        "-a",
        "150",
        "-w",
        str(AUDIO),
        text,
    ])

    if not AUDIO.exists():
        raise RuntimeError(
            "Hindi narration was not generated."
        )


def get_duration():

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(AUDIO),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr
        )

    return float(
        result.stdout.strip()
    )


def create_video():

    duration = get_duration()

    print(
        f"Creating {WIDTH}x{HEIGHT} vertical video "
        f"for {duration:.1f} seconds..."
    )

    filter_graph = (
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/"
        "noto/NotoSansDevanagari-Regular.ttf:"
        "text='दैनिक वैदिक ज्योतिष':"
        "fontcolor=white:"
        "fontsize=64:"
        "x=(w-text_w)/2:"
        "y=110:"
        "box=1:"
        "boxcolor=black@0.45:"
        "boxborderw=24"
    )

    run([
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        (
            f"color=c=0x130B2B:"
            f"s={WIDTH}x{HEIGHT}:"
            f"r={FPS}"
        ),
        "-i",
        str(AUDIO),
        "-vf",
        filter_graph,
        "-t",
        str(duration),
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
        str(VIDEO),
    ])

    if not VIDEO.exists():
        raise RuntimeError(
            "Video was not created."
        )


def main():

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    require("ffmpeg")
    require("ffprobe")
    require("espeak-ng")

    text = read_script()

    create_voice(text)

    create_video()

    print()
    print("======================================")
    print("VIDEO GENERATION SUCCESSFUL")
    print("======================================")
    print(f"Script : {SCRIPT}")
    print(f"Audio  : {AUDIO}")
    print(f"Video  : {VIDEO}")
    print("======================================")


if __name__ == "__main__":
    main()
