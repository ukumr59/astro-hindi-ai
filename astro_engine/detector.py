from .models import TransitEvent
from .rules import SIGN_HI, PLANET_HI

def detect_sign_changes(previous_positions, current_positions):
    prev = {p.planet: p for p in previous_positions}
    events = []
    for cur in current_positions:
        old = prev.get(cur.planet)
        if old and old.sign_index != cur.sign_index:
            events.append(TransitEvent(
                planet=cur.planet,
                event_type="sign_change",
                from_sign=SIGN_HI[old.sign_index],
                to_sign=SIGN_HI[cur.sign_index],
                importance=90 if cur.planet in {"Jupiter", "Saturn", "Rahu", "Ketu"} else 70,
                description_hi=(
                    f"{PLANET_HI[cur.planet]} ने {SIGN_HI[old.sign_index]} से "
                    f"{SIGN_HI[cur.sign_index]} राशि में प्रवेश किया है।"
                )
            ))
    return sorted(events, key=lambda e: e.importance, reverse=True)
