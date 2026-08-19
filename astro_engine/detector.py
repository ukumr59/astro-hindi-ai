from .models import TransitEvent
from .rules import SIGN_HI, PLANET_HI


# Maximum realistic apparent movement in one day.
#
# These limits are deliberately generous so that genuine
# sign transitions are not accidentally rejected.
MAX_DAILY_MOTION = {
    "Sun": 2.0,
    "Moon": 20.0,
    "Mercury": 5.0,
    "Venus": 4.0,
    "Mars": 3.0,
    "Jupiter": 2.0,
    "Saturn": 2.0,
    "Rahu": 0.5,
    "Ketu": 0.5,
}


def normalize_longitude(value):
    """Keep longitude between 0 and 360 degrees."""
    return value % 360.0


def sign_from_longitude(longitude):
    """
    Calculate the zodiac sign directly from longitude.

    This is intentionally NOT taken from PlanetPosition.sign_index.
    The longitude is our source of truth.
    """
    longitude = normalize_longitude(longitude)

    return int(longitude // 30)


def angular_distance(old_longitude, new_longitude):
    """
    Calculate the shortest angular movement between two positions.

    Correctly handles the 0°/360° boundary.
    """
    old_longitude = normalize_longitude(old_longitude)
    new_longitude = normalize_longitude(new_longitude)

    difference = new_longitude - old_longitude

    return ((difference + 180.0) % 360.0) - 180.0


def detect_sign_changes(previous_positions, current_positions):
    """
    Detect genuine planetary sign transitions.

    Safeguards:

    1. Sign is recalculated directly from longitude.
    2. Unrealistic one-day jumps are rejected.
    3. 0°/360° longitude wrapping is handled correctly.
    4. Rahu/Ketu are subject to a strict motion limit.
    5. Existing sign_index values are not blindly trusted.
    """

    previous = {
        p.planet: p
        for p in previous_positions
    }

    events = []

    for current in current_positions:

        old = previous.get(current.planet)

        if old is None:
            continue

        old_longitude = normalize_longitude(
            old.longitude
        )

        current_longitude = normalize_longitude(
            current.longitude
        )

        # Calculate actual apparent movement.
        movement = angular_distance(
            old_longitude,
            current_longitude
        )

        movement_abs = abs(movement)

        # Determine signs directly from astronomical longitude.
        old_sign_index = sign_from_longitude(
            old_longitude
        )

        current_sign_index = sign_from_longitude(
            current_longitude
        )

        # No sign change.
        if old_sign_index == current_sign_index:
            continue

        # ---------------------------------------------------------
        # SANITY CHECK
        # ---------------------------------------------------------
        #
        # A planet cannot suddenly jump an entire zodiac sign
        # between two daily observations.
        #
        # This prevents corrupt/stale/mismatched data from being
        # interpreted as a planetary transition.
        #

        allowed_motion = MAX_DAILY_MOTION.get(
            current.planet,
            5.0
        )

        if movement_abs > allowed_motion:
            print(
                f"IGNORED FALSE TRANSITION: "
                f"{current.planet} "
                f"{old_longitude:.2f}° → "
                f"{current_longitude:.2f}° "
                f"(movement {movement_abs:.2f}°)"
            )

            continue

        # ---------------------------------------------------------
        # VALID TRANSITION
        # ---------------------------------------------------------

        if current.planet in {
            "Jupiter",
            "Saturn",
            "Rahu",
            "Ketu",
        }:
            importance = 90

        elif current.planet in {
            "Mars",
            "Mercury",
            "Venus",
        }:
            importance = 75

        else:
            importance = 70

        planet_name = PLANET_HI.get(
            current.planet,
            current.planet
        )

        from_sign = SIGN_HI[
            old_sign_index
        ]

        to_sign = SIGN_HI[
            current_sign_index
        ]

        description = (
            f"{planet_name} ने "
            f"{from_sign} से "
            f"{to_sign} राशि में प्रवेश किया है।"
        )

        events.append(
            TransitEvent(
                planet=current.planet,
                event_type="sign_change",
                from_sign=from_sign,
                to_sign=to_sign,
                importance=importance,
                description_hi=description
            )
        )

    return sorted(
        events,
        key=lambda event: event.importance,
        reverse=True
    )
