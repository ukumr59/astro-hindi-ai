"""AstroCreatorAgent — Generates high-retention Hindi astrological video scripts."""
import logging
from typing import Dict, List, Optional

from content_engine.script import build_daily_script
from .models import AstroBrief, ScriptDraft

logger = logging.getLogger("agents.creator")


class AstroCreatorAgent:
    """Agent that creates platform-native Hindi video scripts and metadata."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def run(
        self,
        brief: AstroBrief,
        target_noon,
        positions: List,
        events: List,
        revision: int = 0,
        feedback: str = "",
    ) -> ScriptDraft:
        """Generate or revise the Hindi script draft."""
        logger.info(f"Creator Agent: Generating script (Revision: {revision})")

        # Use the core diversity-aware content engine for the base script
        full_script = build_daily_script(target_noon, positions, events)

        # In revision mode, refine the hook and tone based on feedback
        hook = brief.macro_hook
        if revision > 0 and feedback:
            logger.info(f"Creator Agent: Refining draft with feedback: {feedback}")
            # Prepend an even more direct, engaging opening hook
            hook = f"{hook} ग्रहों के शुभ-अशुभ प्रभावों से बचने के सरल और सटीक उपाय भी जानेंगे।"

        title = brief.suggested_titles[0]
        description = (
            f"{brief.main_theme}\n\n"
            f"AstroPratidin पर आपका स्वागत है। इस वीडियो में जानिए {brief.publication_date} का संपूर्ण राशिफल "
            f"एवं 12 राशियों के लिए सटीक ग्रह गोचर फल और सरल उपाय।\n\n"
            f"📌 प्रमुख आकर्षण:\n"
            f"- 12 राशियों का दैनिक फलादेश\n"
            f"- आज का लकी कलर और लकी नंबर\n"
            f"- नकारात्मक प्रभावों से बचने के सरल वैदिक उपाय\n\n"
            f"कृपया चैनल को लाइक, शेयर और सब्सक्राइब करें!\n"
            f"#AstroPratidin #Rashifal #Astrology"
        )

        draft = ScriptDraft(
            title=title,
            description=description,
            tags=brief.suggested_tags,
            hook=hook,
            intro=f"नमस्कार! AstroPratidin के दैनिक राशिफल में आपका स्वागत है। {hook}",
            rashi_sections={},  # Embedded within full_script_md
            outro="यह सामान्य वैदिक गोचर विश्लेषण है। व्यक्तिगत कुंडली के लिए संपर्क करें। लाइक, शेयर और सब्सक्राइब जरूर करें। धन्यवाद!",
            full_script_md=full_script,
            revision=revision,
            feedback_incorporated=feedback,
        )
        return draft
