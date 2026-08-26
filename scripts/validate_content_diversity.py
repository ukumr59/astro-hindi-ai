"""Guardrail against regression to a single daily production template."""
from datetime import date, timedelta
from pathlib import Path
import json

from content_engine.diversity import select_content_profile


def main():
    start = date.today()
    profiles = [select_content_profile(start + timedelta(days=i)) for i in range(14)]
    keys = {p.key for p in profiles}
    visuals = {p.visual_style for p in profiles}
    if len(keys) < 4:
        raise SystemExit(f"Content rotation too narrow: only {len(keys)} editorial profiles in 14 days")
    if len(visuals) < 4:
        raise SystemExit(f"Visual rotation too narrow: only {len(visuals)} styles in 14 days")

    manifest_path = Path("output/content_profile.json")
    script_path = Path("output/daily_script.md")
    if not manifest_path.exists() or not script_path.exists():
        raise SystemExit("Missing content diversity outputs")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {"key", "intro_style", "event_style", "rashi_style", "visual_style", "publication_date"}
    missing = required - set(manifest)
    if missing:
        raise SystemExit(f"Incomplete content profile: missing {sorted(missing)}")
    script = script_path.read_text(encoding="utf-8")
    if len(script.split()) < 120:
        raise SystemExit("Daily script unexpectedly short")
    print(f"CONTENT DIVERSITY: PASS ({len(keys)} editorial profiles / {len(visuals)} visual styles over 14 days)")
    print(f"TODAY PROFILE: {manifest['key']} / rashi={manifest['rashi_style']} / visual={manifest['visual_style']}")


if __name__ == "__main__":
    main()
