"""YPP-oriented guardrail against repetitive or thin daily productions."""
from datetime import date, timedelta
from pathlib import Path
import json
import re

from content_engine.diversity import select_content_profile

RASHIS = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
PLANETS = ["सूर्य", "चंद्रमा", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "राहु", "केतु"]


def _sections(script):
    positions = [m.start() for m in re.finditer(r"(?m)^(?:" + "|".join(RASHIS) + r") राशि", script)]
    return [script[a:b] for a, b in zip(positions, positions[1:] + [len(script)])]


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

    sections = _sections(script)
    if len(sections) != 12:
        raise SystemExit(f"Expected 12 distinct Rashi sections, found {len(sections)}")

    for index, section in enumerate(sections, 1):
        words = section.split()
        planet_hits = {p for p in PLANETS if p in section}
        house_hits = set(re.findall(r"(?:1[0-2]|[1-9])वें भाव", section))
        if len(words) < 90:
            raise SystemExit(f"Rashi section {index} is too thin: {len(words)} words")
        if len(planet_hits) < 2:
            raise SystemExit(f"Rashi section {index} lacks substantive planetary evidence")
        if len(house_hits) < 2:
            raise SystemExit(f"Rashi section {index} lacks multiple house-specific signals")

    print(f"CONTENT DIVERSITY: PASS ({len(keys)} editorial profiles / {len(visuals)} visual styles over 14 days)")
    print("YPP SUBSTANCE GUARD: PASS (12 Rashi sections; each has multiple planetary + house-specific signals)")
    print(f"TODAY PROFILE: {manifest['key']} / rashi={manifest['rashi_style']} / visual={manifest['visual_style']}")


if __name__ == "__main__":
    main()
