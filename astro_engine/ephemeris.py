from datetime import datetime, timedelta, timezone

import swisseph as swe

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


# Swiss Ephemeris / Moshier planetary bodies.
# Moshier is used deliberately so GitHub Actions does NOT need
# to download a JPL BSP file from NASA during every run.
PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
}

# Sidereal Lahiri / Chitrapaksha.
swe.set_sid_mode(swe.SIDM_LAHIRI)


class EphemerisBackend:
    """Interface for planetary-position providers."""

    def positions(self, when: datetime):
        raise NotImplementedError


class RealEphemeris(EphemerisBackend):
    """
    Offline real-astronomy planetary engine.

    Provider:
        Swiss Ephemeris Moshier calculations bundled with pyswisseph.

    Zodiac:
        Sidereal zodiac using Lahiri / Chitrapaksha ayanamsa.

    Planets:
        Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn.

    Lunar nodes:
        Mean Rahu and Ketu using the Swiss Ephemeris mean node.

    Important production property:
        No network request is made while calculating planetary positions.
        This prevents GitHub Actions from failing when the JPL DE440s
        download endpoint times out.
    """

    def __init__(self):
        # FLG_MOSEPH uses the built-in Moshier analytical ephemeris.
        # It requires no .bsp files and therefore works offline.
        self.flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    @staticmethod
    def normalize(degrees):
        return degrees % 360.0

    @staticmethod
    def julian_day(when):
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        utc = when.astimezone(timezone.utc)
        hour = (
            utc.hour
            + utc.minute / 60.0
            + utc.second / 3600.0
            + utc.microsecond / 3600000000.0
        )
        return swe.julday(utc.year, utc.month, utc.day, hour)

    @classmethod
    def lahiri_ayanamsa(cls, jd):
        # Returned by Swiss Ephemeris in degrees for the configured
        # Lahiri sidereal mode. Keeping this helper preserves the old API.
        return float(swe.get_ayanamsa_ut(jd))

    def _longitude(self, planet_id, jd):
        xx, _ = swe.calc_ut(jd, planet_id, self.flags)
        return self.normalize(float(xx[0]))

    def sidereal_longitude(self, body_name, jd):
        return self._longitude(PLANETS[body_name], jd)

    @staticmethod
    def sign_index(longitude):
        longitude = longitude % 360.0
        return int(longitude // 30)

    def is_retrograde(self, body_name, jd):
        before = self._longitude(PLANETS[body_name], jd - 0.5)
        after = self._longitude(PLANETS[body_name], jd + 0.5)
        movement = ((after - before + 180.0) % 360.0) - 180.0
        return movement < 0

    def positions(self, when=None):
        if when is None:
            when = datetime.now(timezone.utc)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)

        jd = self.julian_day(when)
        results = []

        for planet, planet_id in PLANETS.items():
            longitude = self._longitude(planet_id, jd)
            retrograde = False
            if planet not in {"Sun", "Moon"}:
                retrograde = self.is_retrograde(planet, jd)
            results.append(
                PlanetPosition(
                    planet=planet,
                    longitude=longitude,
                    sign_index=self.sign_index(longitude),
                    retrograde=retrograde,
                )
            )

        # Mean ascending lunar node = Rahu.
        rahu, _ = swe.calc_ut(jd, swe.MEAN_NODE, self.flags)
        rahu_longitude = self.normalize(float(rahu[0]))
        ketu_longitude = self.normalize(rahu_longitude + 180.0)

        results.append(
            PlanetPosition(
                planet="Rahu",
                longitude=rahu_longitude,
                sign_index=self.sign_index(rahu_longitude),
                retrograde=True,
            )
        )
        results.append(
            PlanetPosition(
                planet="Ketu",
                longitude=ketu_longitude,
                sign_index=self.sign_index(ketu_longitude),
                retrograde=True,
            )
        )

        return results


# Backward compatibility: existing modules import Ephemeris.
Ephemeris = RealEphemeris
