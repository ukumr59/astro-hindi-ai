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


# Real planetary bodies available in JPL DE440s.
#
# Skyfield's DE440s ephemeris uses barycenters for
# Mars, Jupiter and Saturn.
PLANETS = {
    "Sun": "SUN",
    "Moon": "MOON",
    "Mercury": "MERCURY",
    "Venus": "VENUS",
    "Mars": "MARS BARYCENTER",
    "Jupiter": "JUPITER BARYCENTER",
    "Saturn": "SATURN BARYCENTER",
}


class EphemerisBackend:
    """Interface for planetary-position providers."""

    def positions(self, when: datetime):
        raise NotImplementedError


class RealEphemeris(EphemerisBackend):
    """
    Real astronomical planetary engine.

    Astronomical source:
        JPL DE440s via Skyfield.

    Zodiac:
        Sidereal zodiac using Lahiri / Chitrapaksha ayanamsa.

    Planets:
        Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn.

    Lunar nodes:
        Mean Rahu and Ketu, converted to sidereal longitude
        using the same Lahiri ayanamsa.

    This engine is designed to run automatically on GitHub Actions.
    """

    def __init__(self):

        self.ts = load.timescale()

        # JPL DE440s covers 1849–2150.
        self.planets = load("de440s.bsp")

        self.earth = self.planets["EARTH"]

    # ---------------------------------------------------------
    # GENERAL ANGLE FUNCTIONS
    # ---------------------------------------------------------

    @staticmethod
    def normalize(degrees):
        """Normalize longitude to 0–360 degrees."""

        return degrees % 360.0

    @staticmethod
    def julian_centuries(jd):
        """Julian centuries from J2000.0."""

        return (jd - 2451545.0) / 36525.0

    # ---------------------------------------------------------
    # LAHIRI AYANAMSA
    # ---------------------------------------------------------

    @classmethod
    def lahiri_ayanamsa(cls, jd):
        """
        Approximate Lahiri / Chitrapaksha ayanamsa.

        The calculation is isolated in this function so that
        it can later be replaced by a higher precision
        implementation without changing the rest of the engine.
        """

        t = cls.julian_centuries(jd)

        return (
            23.8569
            + 1.3969713 * t
            + 0.0003086 * t * t
        )

    # ---------------------------------------------------------
    # TROPICAL LONGITUDE
    # ---------------------------------------------------------

    def tropical_longitude(self, body_name, t):
        """
        Calculate geocentric apparent ecliptic longitude.
        """

        body = self.planets[body_name]

        astrometric = self.earth.at(t).observe(body)

        apparent = astrometric.apparent()

        _, longitude, _ = apparent.ecliptic_latlon()

        return float(longitude.degrees)

    # ---------------------------------------------------------
    # SIDEREAL LONGITUDE
    # ---------------------------------------------------------

    def sidereal_longitude(self, body_name, t):
        """
        Convert tropical longitude to Lahiri sidereal longitude.
        """

        tropical = self.tropical_longitude(
            body_name,
            t
        )

        ayanamsa = self.lahiri_ayanamsa(
            t.tt
        )

        return self.normalize(
            tropical - ayanamsa
        )

    # ---------------------------------------------------------
    # RASHI
    # ---------------------------------------------------------

    @staticmethod
    def sign_index(longitude):
        """
        Convert sidereal longitude to zodiac sign index.

        0 = मेष
        1 = वृषभ
        ...
        11 = मीन
        """

        longitude = longitude % 360.0

        return int(longitude // 30)

    # ---------------------------------------------------------
    # RETROGRADE
    # ---------------------------------------------------------

    def is_retrograde(self, body_name, t):
        """
        Estimate apparent retrograde motion.

        The planetary longitude is checked 12 hours before
        and 12 hours after the requested time.
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

        movement = (
            (after - before + 180.0)
            % 360.0
        ) - 180.0

        return movement < 0

    # ---------------------------------------------------------
    # MAIN POSITION CALCULATION
    # ---------------------------------------------------------

    def positions(self, when=None):

        if when is None:
            when = datetime.now(timezone.utc)

        if when.tzinfo is None:
            when = when.replace(
                tzinfo=timezone.utc
            )

        t = self.ts.from_datetime(
            when
        )

        results = []

        # -----------------------------------------------------
        # SUN THROUGH SATURN
        # -----------------------------------------------------

        for planet, body_name in PLANETS.items():

            longitude = self.sidereal_longitude(
                body_name,
                t
            )

            sign_index = self.sign_index(
                longitude
            )

            retrograde = False

            if planet not in {
                "Sun",
                "Moon"
            }:
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

        # -----------------------------------------------------
        # RAHU
        # -----------------------------------------------------
        #
        # Calculate MEAN lunar ascending node.
        #
        # IMPORTANT:
        # The classical node formula produces a TROPICAL
        # longitude.
        #
        # Therefore we MUST subtract Lahiri ayanamsa before
        # assigning the Vedic / sidereal Rashi.
        #

        T = self.julian_centuries(
            t.tt
        )

        raw_rahu = self.normalize(
            125.04452
            - 1934.136261 * T
            + 0.0020708 * T * T
            + (T * T * T) / 450000.0
        )

        # Convert tropical Rahu to sidereal Rahu.
        ayanamsa = self.lahiri_ayanamsa(
            t.tt
        )

        rahu = self.normalize(
            raw_rahu - ayanamsa
        )

        # -----------------------------------------------------
        # KETU
        # -----------------------------------------------------
        #
        # Ketu is exactly 180° opposite Rahu.
        #

        ketu = self.normalize(
            rahu + 180.0
        )

        # -----------------------------------------------------
        # RAHU RESULT
        # -----------------------------------------------------

        results.append(
            PlanetPosition(
                planet="Rahu",
                longitude=rahu,
                sign_index=self.sign_index(
                    rahu
                ),
                retrograde=True
            )
        )

        # -----------------------------------------------------
        # KETU RESULT
        # -----------------------------------------------------

        results.append(
            PlanetPosition(
                planet="Ketu",
                longitude=ketu,
                sign_index=self.sign_index(
                    ketu
                ),
                retrograde=True
            )
        )

        return results


# -------------------------------------------------------------
# BACKWARD COMPATIBILITY
# -------------------------------------------------------------
#
# Existing modules may import Ephemeris.
# Keep this alias so that the rest of the project does not break.
#

Ephemeris = RealEphemeris
