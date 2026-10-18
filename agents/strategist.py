"""AstroStrategistAgent — Analyzes astrological data and designs content strategy."""
import json
import logging
import os
from typing import Dict, List

from .models import AstroBrief

logger = logging.getLogger("agents.strategist")


class AstroStrategistAgent:
    """Agent that extracts macro trends from planetary positions and formulates content strategy."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")

    def run(self, publication_date: str, positions: List[Dict], events: List[Dict]) -> AstroBrief:
        """Analyze positions and events to build the AstroBrief."""
        logger.info(f"Strategist Agent: Analyzing astrological data for {publication_date}")

        # Identify significant planetary aspects
        aspects = []
        high_impact = []
        for p in positions:
            name = p.get("planet")
            sign = p.get("sign", "")
            if p.get("retrograde"):
                aspects.append(f"{name} वक्री गति में ({sign})")
            if name in ["Jupiter", "Saturn", "Rahu", "Ketu"]:
                high_impact.append(sign)

        for e in events:
            desc = e.get("description_hi") or f"{e.get('planet')} गोचर"
            aspects.append(desc)
            if e.get("to_sign"):
                high_impact.append(e.get("to_sign"))

        # Deduplicate high impact rashis
        high_impact = list(dict.fromkeys([s for s in high_impact if s]))[:4]
        if not high_impact:
            high_impact = ["मेष", "सिंह", "तुला", "धनु"]

        # Strategy theme
        if events:
            main_theme = f"ग्रह गोचर और राशि परिवर्तन विशेष: {events[0].get('description_hi', 'प्रमुख गोचर')}"
            macro_hook = f"सावधान! आज ग्रहों की चाल में बड़ा फेरबदल। जानिए आपकी राशि पर इसका क्या होगा गहरा असर।"
        elif any("वक्री" in a for a in aspects):
            main_theme = "वक्री ग्रहों का प्रभाव और संभलकर चलने के संकेत"
            macro_hook = "वक्री ग्रहों की विशेष दृष्टि! किन राशियों को आज रहना होगा सबसे ज्यादा सतर्क?"
        else:
            main_theme = "दैनिक वैदिक गोचर: कर्म, निर्णय और संतुलन का मार्गदर्शन"
            macro_hook = "आज का दिन किन राशियों के लिए खोलेगा किस्मत के ताले और किन्हें बरतनी होगी सावधानी?"

        suggested_titles = [
            f"दैनिक राशिफल {publication_date} | 12 राशियों का सटीक भविष्यफल | AstroPratidin",
            f"आज का राशिफल: {high_impact[0]} और {high_impact[1]} राशि वाले रहें सावधान! {publication_date}",
            f"{publication_date} राशिफल: जानिए कौन सी राशियां रहेंगी सबसे भाग्यशाली | AstroPratidin",
        ]

        suggested_tags = [
            "AstroPratidin", "Rashifal", "Horoscope", "DailyHoroscope",
            "AstrologyInHindi", "AajKaRashifal", "JyotishVigyan",
            "VedicAstrology", publication_date,
        ]

        brief = AstroBrief(
            publication_date=publication_date,
            main_theme=main_theme,
            macro_hook=macro_hook,
            key_planetary_aspects=aspects,
            high_impact_rashis=high_impact,
            suggested_titles=suggested_titles,
            suggested_tags=suggested_tags,
        )
        logger.info(f"Strategist Agent: Brief created with theme '{main_theme}'")
        return brief
