from pathlib import Path

def render():
    script = Path("output/daily_script.md")
    if not script.exists():
        raise SystemExit("Run the astrology pipeline first.")
    print("Video renderer scaffold ready.")
    print("Next: FFmpeg scene composition + offline Hindi TTS.")

if __name__ == "__main__":
    render()
