from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class PlanetPosition:
    planet: str
    longitude: float
    sign_index: int
    retrograde: bool = False

@dataclass
class TransitEvent:
    planet: str
    event_type: str
    from_sign: str
    to_sign: str
    importance: int
    description_hi: str

@dataclass
class DailyAstroState:
    date: datetime
    positions: List[PlanetPosition]
    events: List[TransitEvent]
