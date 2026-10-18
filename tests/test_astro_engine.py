"""Unit tests for the astro_engine calculation and detection modules."""
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from astro_engine.models import PlanetPosition, TransitEvent, DailyAstroState
from astro_engine.detector import (
    normalize_longitude,
    sign_from_longitude,
    angular_distance,
    detect_sign_changes,
)
from astro_engine.rules import SIGN_HI, PLANET_HI, rashi_summary
from astro_engine.main import format_position, build_report

IST = ZoneInfo("Asia/Kolkata")


def test_normalize_longitude():
    assert normalize_longitude(0.0) == 0.0
    assert normalize_longitude(360.0) == 0.0
    assert normalize_longitude(365.5) == 5.5
    assert normalize_longitude(-10.0) == 350.0


def test_sign_from_longitude():
    # 0 - 29.99 degrees -> Aries (0)
    assert sign_from_longitude(0.0) == 0
    assert sign_from_longitude(15.5) == 0
    assert sign_from_longitude(29.99) == 0
    # 30.0 degrees -> Taurus (1)
    assert sign_from_longitude(30.0) == 1
    # 330 - 359.99 degrees -> Pisces (11)
    assert sign_from_longitude(355.0) == 11


def test_angular_distance():
    # Normal forward motion
    assert angular_distance(10.0, 15.0) == 5.0
    # Boundary wrap-around (Pisces to Aries)
    assert angular_distance(358.0, 2.0) == 4.0
    # Retrograde motion wrap-around
    assert angular_distance(2.0, 358.0) == -4.0


def test_detect_sign_changes():
    # Sun moves from Pisces (359 deg) to Aries (1 deg)
    prev = [PlanetPosition(planet="Sun", longitude=359.0, sign_index=11, retrograde=False)]
    curr = [PlanetPosition(planet="Sun", longitude=1.0, sign_index=0, retrograde=False)]
    events = detect_sign_changes(prev, curr)
    assert len(events) == 1
    assert events[0].planet == "Sun"
    assert events[0].from_sign == SIGN_HI[11]
    assert events[0].to_sign == SIGN_HI[0]


def test_format_position():
    pos = PlanetPosition(planet="Sun", longitude=45.5, sign_index=1, retrograde=False)
    res = format_position(pos)
    assert "सूर्य" in res
    assert "45.50°" in res
    assert "वृषभ" in res

    pos_retro = PlanetPosition(planet="Saturn", longitude=310.2, sign_index=10, retrograde=True)
    res_retro = format_position(pos_retro)
    assert "शनि" in res_retro
    assert "वक्री" in res_retro


def test_build_report():
    positions = [
        PlanetPosition(planet="Sun", longitude=10.0, sign_index=0, retrograde=False),
        PlanetPosition(planet="Moon", longitude=40.0, sign_index=1, retrograde=False),
    ]
    events = [
        TransitEvent(
            planet="Sun",
            event_type="SIGN_CHANGE",
            from_sign="मीन",
            to_sign="मेष",
            importance=5,
            description_hi="सूर्य का मेष राशि में प्रवेश",
        )
    ]
    target_date = datetime(2026, 10, 19, 12, 0, tzinfo=IST).date()
    report = build_report(positions, events, target_date)
    assert "दैनिक ग्रह स्थिति रिपोर्ट" in report
    assert "सूर्य: 10.00° मेष" in report
    assert "सूर्य का मेष राशि में प्रवेश" in report
