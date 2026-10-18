"""AstroReviewerAgent — Quality Control & Decision Gatekeeper for Astrology Content."""
import logging
import re
from typing import Tuple

from .models import AstroBrief, ReviewVerdict, ScriptDraft

logger = logging.getLogger("agents.reviewer")

CANONICAL_RASHIS = [
    "मेष", "वृषभ", "मिथुन", "कर्क",
    "सिंह", "कन्या", "तुला", "वृश्चिक",
    "धनु", "मकर", "कुंभ", "मीन",
]


class AstroReviewerAgent:
    """Agent that critiques, scores, and decides whether a script is ready for production."""

    def __init__(self, pass_threshold: float = 8.0):
        self.pass_threshold = pass_threshold

    def run(
        self,
        draft: ScriptDraft,
        brief: AstroBrief,
        revision_count: int = 0,
        max_revisions: int = 2,
    ) -> ReviewVerdict:
        """Evaluate the script draft and issue a pass/fail verdict."""
        logger.info(f"Reviewer Agent: Inspecting draft (Revision {revision_count})")

        script = draft.full_script_md
        feedback_notes = []

        # 1. Astrological Fidelity Check (All 12 Rashis must exist and have unique headings)
        missing_rashis = []
        for rashi in CANONICAL_RASHIS:
            if not re.search(rf"\b{re.escape(rashi)}\s+राशि", script):
                missing_rashis.append(rashi)

        if missing_rashis:
            fidelity_score = max(2.0, 10.0 - (len(missing_rashis) * 1.5))
            feedback_notes.append(f"Missing headings for rashis: {', '.join(missing_rashis)}")
        else:
            fidelity_score = 10.0

        # 2. Hook and Engagement Check
        hook = draft.hook
        if len(hook) > 20 and ("?" in hook or "!" in hook or "।" in hook):
            hook_score = 9.5
        elif len(hook) > 10:
            hook_score = 7.5
            feedback_notes.append("Opening hook could be more compelling and provocative.")
        else:
            hook_score = 4.0
            feedback_notes.append("Opening hook is too short or missing.")

        # 3. Emotional Tone & Constructiveness (Empowerment vs Fear)
        alarmist_words = ["विनाश", "भयंकर तबाही", "सर्वनाश", "मौत"]
        found_alarmist = [w for w in alarmist_words if w in script]
        if found_alarmist:
            resonance_score = 5.0
            feedback_notes.append(f"Excessive fatalistic/alarmist vocabulary detected: {found_alarmist}. Soften tone.")
        else:
            resonance_score = 9.5

        # 4. Platform Policy & Metadata Compliance
        compliance_issues = []
        if len(draft.title) > 100:
            compliance_issues.append("Title exceeds YouTube 100 character limit.")
        if len(draft.description) > 5000:
            compliance_issues.append("Description exceeds 5000 character limit.")
        if not draft.tags:
            compliance_issues.append("Tags list is empty.")

        if compliance_issues:
            policy_score = 6.0
            feedback_notes.extend(compliance_issues)
        else:
            policy_score = 10.0

        # Weighted Overall Score
        overall_score = round(
            (fidelity_score * 0.40) +
            (hook_score * 0.25) +
            (resonance_score * 0.20) +
            (policy_score * 0.15),
            2,
        )

        # Decision
        if revision_count >= max_revisions:
            approved = True
            logger.info(f"Reviewer Agent: Max revisions ({max_revisions}) reached. Auto-approving with score {overall_score}")
        else:
            approved = overall_score >= self.pass_threshold

        feedback = " | ".join(feedback_notes) if feedback_notes else "Draft meets all AstroPratidin quality and policy standards."

        verdict = ReviewVerdict(
            approved=approved,
            overall_score=overall_score,
            astrological_fidelity_score=fidelity_score,
            viewer_hook_score=hook_score,
            emotional_resonance_score=resonance_score,
            policy_compliance_score=policy_score,
            feedback=feedback,
            revision_count=revision_count,
        )

        logger.info(f"Reviewer Agent: Verdict -> Approved={approved}, Score={overall_score}/10")
        return verdict
