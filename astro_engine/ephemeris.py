from datetime import datetime, timedelta, timezone

from skyfield.api import load

from .models import PlanetPosition


SIGN_HI = [
    "मेष",
    "वृषभ",
    "मिथुन",
    "कर्क",
    "सिंह",
    "कन्या",
    "तुला",
    "वृश्चिक",
    "धनु",
    "मकर",
    "कुंभ",
    "मीन",
]


PLANETS = {
    "Sun": "sun",
    "Moon": "moon",
    "Mercury": "mercury",
    "Venus": "venus",
    "Mars": "mars",
    "Jupiter": "jupiter",
    "Saturn": "saturn",
}


class EphemerisBackend:
    """Interface for planetary-position providers."""

    def positions(self, when: datetime):
        raise NotImplementedError


class RealEphemeris(EphemerisBackend):
    """
    Real astronomical planetary engine.

    Astronomical source:
        JPL DE440s via Skyfield

    Zodiac:
        Sidereal zodiac using a Lahiri/Chitrapaksha ayanamsa model.

    Output:
        PlanetPosition objects compatible with the existing
        astrology engine.
    """

    def __init__(self):
        self.ts = load.timescale()

        # JPL DE440s is downloaded automatically by Skyfield
        # the first time it is needed.
        self.planets = load("de440s.bsp")

        self.earth = self.planets["earth"]

    @staticmethod
    def normalize(degrees):
        """Return an angle between 0 and 360 degrees."""
        return degrees % 360.0

    @staticmethod
    def julian_centuries(jd):
        """Julian centuries measured from J2000.0."""
        return (jd - 2451545.0) / 36525.0

    @classmethod
    def lahiri_ayanamsa(cls, jd):
        """
        Approximate Lahiri / Chitrapaksha ayanamsa.

        Reference epoch:
            J2000.0

        The formula is isolated here so it can later be replaced
        with a higher-precision implementation without changing
        the rest of the application.
        """

        t = cls.julian_centuries(jd)

        return (
            23.8569
            + 1.3969713 * t
            + 0.0003086 * t * t
        )

    def tropical_longitude(self, body_name, t):
        """Calculate geocentric apparent ecliptic longitude."""

        body = self.planets[body_name]

        astrometric = self.earth.at(t).observe(body)
        apparent = astrometric.apparent()

        _, longitude, _ = apparent.ecliptic_latlon()

        return float(longitude.degrees)

    def sidereal_longitude(self, body_name, t):
        """Convert tropical longitude to Lahiri sidereal longitude."""

        tropical = self.tropical_longitude(body_name, t)

        ayanamsa = self.lahiri_ayanamsa(t.tt)

        return self.normalize(tropical - ayanamsa)

    @staticmethod
    def sign_index(longitude):
        """Convert longitude to a 0–11 zodiac-sign index."""
        return int(longitude // 30)

    def is_retrograde(self, body_name, t):
        """
        Estimate apparent retrograde motion by comparing
        sidereal longitude 12 hours before and after the
        requested time.
        """

        dt = t.utc_datetime()

        before_time = self.ts.from_datetime(
            dt - timedelta(hours=12)
        )

        after_time = self.ts.from_datetime(
            dt + timedelta(hours=12)
        )

        before = self.sidereal_longitude(
            body_name,
            before_time
        )

        after = self.sidereal_longitude(
            body_name,
            after_time
        )

        movement = ((after - before + 180.0) % 360.0) - 180.0

        return movement < 0

    def positions(self, when=None):

        if when is None:
            when = datetime.now(timezone.utc)

        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)

        t = self.ts.from_datetime(when)

        results = []

        for planet, body_name in PLANETS.items():

            longitude = self.sidereal_longitude(
                body_name,
                t
            )

            sign_index = self.sign_index(longitude)

            retrograde = False

            if planet not in {"Sun", "Moon"}:
                retrograde = self.is_retrograde(
                    body_name,
                    t
                )

            results.append(
                PlanetPosition(
                    planet=planet,
                    longitude=longitude,
                    sign_index=sign_index,
                    retrograde=retrograde
                )
            )

        # ---------------------------------------------------------
        # RAHU
        # ---------------------------------------------------------
        #
        # Mean lunar ascending node.
        #
        # Rahu and Ketu are not physical planets. They are calculated
        # lunar nodes and therefore handled separately.
        #

        T = self.julian_centuries(t.tt)

        rahu = self.normalize(
            125.04452
            - 1934.136261 * T
            + 0.0020708 * T * T
            + (T * T * T) / 450000.0
        )

        ketu = self.normalize(rahu + 180.0)

        results.append(
            PlanetPosition(
                planet="Rahu",
                longitude=rahu,
                sign_index=self.sign_index(rahu),
                retrograde=True
            )
        )

        results.append(
            PlanetPosition(
                planet="Ketu",
                longitude=ketu,
                sign_index=self.sign_index(ketu),
                retrograde=True
            )
        )

        return results


# Backward-compatible alias.
#
# Existing code may still import EphemerisBackend.
# Real production calculations use RealEphemeris.
Ephemeris = RealEphemeris
