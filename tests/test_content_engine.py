"""Unit tests for content_engine script and diversity modules."""
import pytest
from datetime import datetime, date
from zoneinfo import ZoneInfo

from content_engine.script import (
    clean,
    complete_sentences,
    _ending,
    build_daily_script,
    rashi_line,
)
from content_engine.diversity import select_content_profile, profile_manifest
from astro_engine.models import PlanetPosition

IST = ZoneInfo("Asia/Kolkata")


def test_clean_and_ending():
    assert clean("  नमस्ते   दुनिया   ") == "नमस्ते दुनिया"
    assert clean("कुछ।। बात") == "कुछ। बात"
    assert _ending("शुभ दिन") == "शुभ दिन।"
    assert _ending("शुभ दिन।") == "शुभ दिन।"
    assert _ending("शुभ दिन!") == "शुभ दिन!"


def test_complete_sentences():
    text = "पहला वाक्य। दूसरा वाक्य। तीसरा वाक्य। चौथा वाक्य।"
    parts = complete_sentences(text, limit=2)
    assert len(parts) == 2
    assert parts[0] == "पहला वाक्य।"
    assert parts[1] == "दूसरा वाक्य।"


def test_diversity_profiles():
    d1 = date(2026, 10, 19)
    profile1 = select_content_profile(d1)
    assert profile1.key in [
        "day_overview",
        "opportunity_map",
        "caution_balance",
        "planet_story",
        "practical_guide",
        "focus_three",
        "reflection",
    ]
    manifest = profile_manifest(d1)
    assert "visual_style" in manifest
    assert "publication_date" in manifest
    assert "rotation_version" in manifest


def test_build_daily_script_structure():
    target_dt = datetime(2026, 10, 19, 12, 0, tzinfo=IST)
    positions = [
        PlanetPosition(planet="Sun", longitude=15.0, sign_index=0, retrograde=False),
        PlanetPosition(planet="Moon", longitude=45.0, sign_index=1, retrograde=False),
        PlanetPosition(planet="Mars", longitude=75.0, sign_index=2, retrograde=False),
        PlanetPosition(planet="Mercury", longitude=105.0, sign_index=3, retrograde=False),
        PlanetPosition(planet="Jupiter", longitude=135.0, sign_index=4, retrograde=False),
        PlanetPosition(planet="Venus", longitude=165.0, sign_index=5, retrograde=False),
        PlanetPosition(planet="Saturn", longitude=195.0, sign_index=6, retrograde=False),
        PlanetPosition(planet="Rahu", longitude=225.0, sign_index=7, retrograde=False),
        PlanetPosition(planet="Ketu", longitude=45.0, sign_index=1, retrograde=False),
    ]
    events = []
    script = build_daily_script(target_dt, positions, events)
    assert len(script) > 500
    # Must contain sections for all 12 rashis
    expected_rashis = [
        "मेष राशि", "वृषभ राशि", "मिथुन राशि", "कर्क राशि",
        "सिंह राशि", "कन्या राशि", "तुला राशि", "वृश्चिक राशि",
        "धनु राशि", "मकर राशि", "कुंभ राशि", "मीन राशि"
    ]
    for rashi in expected_rashis:
        assert rashi in script, f"Missing {rashi} in generated script"
