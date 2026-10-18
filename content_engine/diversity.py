"""Deterministic editorial diversity for AstroPratidin daily productions.

The selector is date-driven rather than random so retries of the same publication
produce the same editorial package, while adjacent days deliberately rotate among
materially different narrative structures.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
import hashlib
from typing import Dict


@dataclass(frozen=True)
class ContentProfile:
    key: str
    display_name: str
    intro_style: str
    event_style: str
    rashi_style: str
    visual_style: str
    hook: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


PROFILES = (
    ContentProfile(
        "day_overview", "दिन का समग्र संकेत", "overview", "priority", "signal", "classic",
        "आज के ग्रह संकेतों में सबसे पहले दिन की समग्र दिशा समझते हैं।",
    ),
    ContentProfile(
        "opportunity_map", "अवसर और प्रगति मानचित्र", "opportunity", "opportunity", "opportunity", "sunrise",
        "आज किन राशियों के लिए अवसर खुल सकते हैं और किन निर्णयों में धैर्य जरूरी है, जानते हैं।",
    ),
    ContentProfile(
        "caution_balance", "सावधानी और संतुलन", "caution", "risk", "balance", "midnight",
        "आज की कुंजी है सही समय पर सही निर्णय—कहां आगे बढ़ना है और कहां ठहरना है, देखते हैं।",
    ),
    ContentProfile(
        "planet_story", "ग्रहों की कहानी", "planet", "story", "cause_effect", "orbit",
        "आज की राशियों के पीछे कौन से ग्रह संकेत काम कर रहे हैं, सरल भाषा में समझते हैं।",
    ),
    ContentProfile(
        "practical_guide", "व्यावहारिक दैनिक मार्गदर्शिका", "practical", "action", "practical", "earth",
        "आज का राशिफल केवल संकेत नहीं, बल्कि काम, धन और संबंधों के लिए व्यावहारिक दिशा भी देगा।",
    ),
    ContentProfile(
        "focus_three", "आज के तीन मुख्य फोकस", "focus", "three_focus", "focus", "aurora",
        "आज के तीन फोकस हैं—अवसर, सावधानी और संतुलन। इन्हीं के आधार पर बारहों राशियों को समझते हैं।",
    ),
    ContentProfile(
        "reflection", "दिन की ऊर्जा और आत्मचिंतन", "reflection", "reflection", "reflection", "lotus",
        "आज के ग्रह संकेतों को आत्मचिंतन और व्यवहारिक निर्णयों के साथ जोड़कर देखते हैं।",
    ),
)


def publication_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def select_content_profile(value) -> ContentProfile:
    d = publication_date(value)
    # Stable, well-distributed selection. A date always maps to one profile,
    # avoiding accidental output changes when a workflow is retried.
    digest = hashlib.sha256(f"AstroPratidin:{d.isoformat()}:v1".encode()).digest()
    return PROFILES[digest[0] % len(PROFILES)]


def profile_manifest(value) -> Dict[str, str]:
    profile = select_content_profile(value)
    data = profile.to_dict()
    data["publication_date"] = publication_date(value).isoformat()
    data["rotation_version"] = "v1"
    return data
