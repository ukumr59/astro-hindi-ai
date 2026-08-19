from datetime import datetime, timedelta
from pathlib import Path
from .ephemeris import DemoBackend
from .detector import detect_sign_changes
from content_engine.script import build_daily_script

OUT = Path("output")
OUT.mkdir(exist_ok=True)

def run():
    now = datetime.now()
    backend = DemoBackend()
    current = backend.positions(now)
    previous = backend.positions(now - timedelta(days=1))
    events = detect_sign_changes(previous, current)
    script = build_daily_script(now, current, events)
    (OUT / "daily_script.md").write_text(
        f"# दैनिक ग्रह परिवर्तन — {now:%d-%m-%Y}\n\n{script}\n",
        encoding="utf-8"
    )
    print(f"Generated {OUT / 'daily_script.md'}")
    print(f"Detected events: {len(events)}")

if __name__ == "__main__":
    run()
