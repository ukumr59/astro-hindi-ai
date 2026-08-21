"""Build the 12 individual Rashi videos from the already-QA'd V21.9.5 scene/audio assets.

The combined production video remains output/daily_video.mp4. Each individual
video reuses the exact rendered Rashi motion clip and its measured TTS segment,
so branding, typography, deity art, motion, and narration stay identical.
"""
from pathlib import Path
import subprocess

OUT = Path("output")
SCENES = OUT / "video_scenes"
AUDIO = OUT / "audio_segments"
DEST = OUT / "youtube_uploads"

RASHIS = [
    (1, "मेष", "मेष राशि"), (2, "वृषभ", "वृषभ राशि"),
    (3, "मिथुन", "मिथुन राशि"), (4, "कर्क", "कर्क राशि"),
    (5, "सिंह", "सिंह राशि"), (6, "कन्या", "कन्या राशि"),
    (7, "तुला", "तुला राशि"), (8, "वृश्चिक", "वृश्चिक राशि"),
    (9, "धनु", "धनु राशि"), (10, "मकर", "मकर राशि"),
    (11, "कुंभ", "कुंभ राशि"), (12, "मीन", "मीन राशि"),
]


def run(cmd):
    print("RUN:", " ".join(str(x) for x in cmd))
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(result.stdout[-5000:])
    if result.returncode:
        raise SystemExit(result.returncode)


def main():
    if not (OUT / "daily_video.mp4").exists():
        raise SystemExit("Combined V21.9.5 production video is missing")
    DEST.mkdir(parents=True, exist_ok=True)
    for old in DEST.glob("*.mp4"):
        old.unlink()

    for index, key, label in RASHIS:
        motion = SCENES / f"motion_{index:02d}.mp4"
        audio = AUDIO / f"{index:02d}_{key}.mp3"
        target = DEST / f"{index:02d}_{key}.mp4"
        if not motion.exists():
            raise SystemExit(f"Missing QA'd motion clip: {motion}")
        if not audio.exists():
            raise SystemExit(f"Missing measured narration audio: {audio}")
        run([
            "ffmpeg", "-y", "-i", str(motion), "-i", str(audio),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-shortest", "-movflags", "+faststart", str(target),
        ])
        print(f"INDIVIDUAL RASHI VIDEO: PASS — {label} — {target}")

    produced = sorted(DEST.glob("*.mp4"))
    if len(produced) != 12:
        raise SystemExit(f"Expected 12 individual Rashi videos, got {len(produced)}")
    print("12 INDIVIDUAL RASHI VIDEOS: PASS")


if __name__ == "__main__":
    main()
