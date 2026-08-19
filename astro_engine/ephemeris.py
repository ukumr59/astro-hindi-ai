from datetime import datetime
from .models import PlanetPosition

class EphemerisBackend:
    def positions(self, when: datetime):
        raise NotImplementedError

class DemoBackend(EphemerisBackend):
    speeds = {
        "Sun": 0.9856, "Moon": 13.1764, "Mars": 0.524,
        "Mercury": 1.2, "Jupiter": 0.083, "Venus": 1.18,
        "Saturn": 0.033, "Rahu": -0.053, "Ketu": 0.053
    }

    base = {
        "Sun": 150.0, "Moon": 210.0, "Mars": 45.0,
        "Mercury": 135.0, "Jupiter": 70.0, "Venus": 180.0,
        "Saturn": 330.0, "Rahu": 20.0, "Ketu": 200.0
    }

    def positions(self, when: datetime):
        epoch = datetime(2026, 1, 1)
        days = (when - epoch).total_seconds() / 86400
        result = []
        for planet, speed in self.speeds.items():
            lon = (self.base[planet] + speed * days) % 360
            result.append(PlanetPosition(
                planet=planet,
                longitude=lon,
                sign_index=int(lon // 30),
                retrograde=speed < 0
            ))
        return result
