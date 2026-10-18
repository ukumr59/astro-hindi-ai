"""MultiAgentCoordinator — Orchestrates Strategist, Creator, Reviewer, and Notifier agents."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from .models import AgentPipelineState, AstroBrief, ReviewVerdict, ScriptDraft
from .strategist import AstroStrategistAgent
from .creator import AstroCreatorAgent
from .reviewer import AstroReviewerAgent
from .notifier import TelegramNotifier

logger = logging.getLogger("agents.orchestrator")
OUT = Path("output")
IST = ZoneInfo("Asia/Kolkata")


class MultiAgentCoordinator:
    """Orchestrates the multi-agent editorial and quality review pipeline."""

    def __init__(self, max_revisions: int = 2, pass_threshold: float = 8.0):
        self.strategist = AstroStrategistAgent()
        self.creator = AstroCreatorAgent()
        self.reviewer = AstroReviewerAgent(pass_threshold=pass_threshold)
        self.notifier = TelegramNotifier()
        self.max_revisions = max_revisions

    def run_pipeline(
        self,
        target_date: str,
        target_noon: datetime,
        positions: List,
        events: List,
    ) -> ScriptDraft:
        """Execute the Strategist -> Creator <-> Reviewer multi-agent loop."""
        OUT.mkdir(exist_ok=True)
        logger.info(f"Multi-Agent Coordinator: Starting run for {target_date}")

        # Step 1: Strategist Agent
        brief = self.strategist.run(
            publication_date=target_date,
            positions=[{"planet": getattr(p, "planet", ""), "sign": str(getattr(p, "sign_index", "")), "retrograde": getattr(p, "retrograde", False)} for p in positions],
            events=[{"planet": getattr(e, "planet", ""), "description_hi": getattr(e, "description_hi", "")} for e in events],
        )

        # Save brief
        (OUT / "editorial_brief.json").write_text(
            json.dumps(
                {
                    "publication_date": brief.publication_date,
                    "main_theme": brief.main_theme,
                    "macro_hook": brief.macro_hook,
                    "key_planetary_aspects": brief.key_planetary_aspects,
                    "high_impact_rashis": brief.high_impact_rashis,
                    "suggested_titles": brief.suggested_titles,
                    "suggested_tags": brief.suggested_tags,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # Step 2: Creator <-> Reviewer Feedback Loop
        current_revision = 0
        feedback = ""
        final_draft: Optional[ScriptDraft] = None
        final_verdict: Optional[ReviewVerdict] = None

        while current_revision <= self.max_revisions:
            draft = self.creator.run(
                brief=brief,
                target_noon=target_noon,
                positions=positions,
                events=events,
                revision=current_revision,
                feedback=feedback,
            )

            verdict = self.reviewer.run(
                draft=draft,
                brief=brief,
                revision_count=current_revision,
                max_revisions=self.max_revisions,
            )

            final_draft = draft
            final_verdict = verdict

            if verdict.approved:
                logger.info(f"Multi-Agent Coordinator: Script approved on revision {current_revision} (Score: {verdict.overall_score}/10)")
                break

            logger.warning(f"Multi-Agent Coordinator: Revision {current_revision} rejected. Feedback: {verdict.feedback}")
            feedback = verdict.feedback
            current_revision += 1

        # Step 3: Write outputs
        (OUT / "daily_script.md").write_text(final_draft.full_script_md, encoding="utf-8")
        (OUT / "review_verdict.json").write_text(
            json.dumps(
                {
                    "approved": final_verdict.approved,
                    "overall_score": final_verdict.overall_score,
                    "astrological_fidelity_score": final_verdict.astrological_fidelity_score,
                    "viewer_hook_score": final_verdict.viewer_hook_score,
                    "emotional_resonance_score": final_verdict.emotional_resonance_score,
                    "policy_compliance_score": final_verdict.policy_compliance_score,
                    "feedback": final_verdict.feedback,
                    "revisions": final_verdict.revision_count,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # Step 4: Dispatch Notification / Approval Request
        self.notifier.notify_approval_request(
            date_str=target_date,
            title=final_draft.title,
            video_count=13,
            review_score=final_verdict.overall_score,
            review_feedback=final_verdict.feedback,
            transits_count=len(events),
        )

        return final_draft
