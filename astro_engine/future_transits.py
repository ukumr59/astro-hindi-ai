from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .ephemeris import RealEphemeris
from .rules import PLANET_HI, SIGN_HI


IST = ZoneInfo("Asia/Kolkata")
MAJOR_PLANETS = {"Jupiter", "Saturn", "Rahu", "Ketu", "Mars", "Mercury", "Venus"}
SCAN_STEP = timedelta(hours=6)


def _sign(longitude):
    return int((longitude % 360.0) // 30)


def _event_time(backend, planet, left, right, left_sign):
    for _ in range(32):
        middle = left + (right - left) / 2
        position = next(p for p in backend.positions(middle) if p.planet == planet)
        if _sign(position.longitude) == left_sign:
            left = middle
        else:
            right = middle
    return right


def find_major_transits(start, days=7):
    """Find major sign-entry events in the next `days` calendar days.

    The search is performed against the bundled Swiss Ephemeris engine,
    so no external astronomy service is required. Jupiter, Saturn, Rahu,
    Ketu, Mars, Mercury and Venus are treated as major transits, matching
    the production detector's importance tiers (>= 75).
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=IST)
    start = start.astimezone(IST)
    end = start + timedelta(days=days)
    backend = RealEphemeris()

    previous = {p.planet: p for p in backend.positions(start)}
    cursor = start
    found = []
    seen = set()

    while cursor < end:
        nxt = min(cursor + SCAN_STEP, end)
        current = {p.planet: p for p in backend.positions(nxt)}

        for planet in sorted(MAJOR_PLANETS):
            old = previous.get(planet)
            new = current.get(planet)
            if not old or not new:
                continue
            old_sign = _sign(old.longitude)
            new_sign = _sign(new.longitude)
            if old_sign == new_sign:
                continue

            occurrence = _event_time(backend, planet, cursor, nxt, old_sign)
            if occurrence > end:
                continue

            key = (planet, round(occurrence.timestamp()), new_sign)
            if key in seen:
                continue
            seen.add(key)

            importance = 90 if planet in {"Jupiter", "Saturn", "Rahu", "Ketu"} else 75
            from_sign = SIGN_HI[old_sign]
            to_sign = SIGN_HI[new_sign]
            planet_hi = PLANET_HI.get(planet, planet)
            description = f"{planet_hi} का {from_sign} से {to_sign} राशि में प्रवेश"
            found.append({
                "id": f"{planet}-{occurrence.astimezone(IST).strftime('%Y%m%d%H%M')}-{new_sign}",
                "planet": planet,
                "planet_hi": planet_hi,
                "from_sign": from_sign,
                "to_sign": to_sign,
                "importance": importance,
                "description_hi": description,
                "occurrence_utc": occurrence.astimezone(__import__('datetime').timezone.utc).isoformat(),
                "occurrence_ist": occurrence.astimezone(IST).isoformat(),
                "publish_on_ist": (occurrence.astimezone(IST).date() - timedelta(days=7)).isoformat(),
            })

        previous = current
        cursor = nxt

    return sorted(found, key=lambda x: (x["occurrence_ist"], -x["importance"]))
