"""Unit tests for the AstroPratidin Multi-Agent System."""
from datetime import datetime, date
from zoneinfo import ZoneInfo
import pytest

from agents.models import AstroBrief, ScriptDraft, ReviewVerdict
from agents.strategist import AstroStrategistAgent
from agents.creator import AstroCreatorAgent
from agents.reviewer import AstroReviewerAgent
from agents.notifier import TelegramNotifier
from agents.orchestrator import MultiAgentCoordinator
from astro_engine.models import PlanetPosition

IST = ZoneInfo("Asia/Kolkata")


def test_strategist_agent():
    agent = AstroStrategistAgent()
    positions = [
        {"planet": "Sun", "sign": "मेष", "retrograde": False},
        {"planet": "Saturn", "sign": "कुंभ", "retrograde": True},
    ]
    events = [
        {"planet": "Sun", "description_hi": "सूर्य का मेष राशि में प्रवेश", "to_sign": "मेष"}
    ]
    brief = agent.run("2026-10-19", positions, events)
    assert brief.publication_date == "2026-10-19"
    assert "गोचर" in brief.main_theme
    assert len(brief.suggested_titles) >= 1
    assert "AstroPratidin" in brief.suggested_tags


def test_creator_and_reviewer_agent_loop():
    strategist = AstroStrategistAgent()
    creator = AstroCreatorAgent()
    reviewer = AstroReviewerAgent(pass_threshold=8.0)

    target_dt = datetime(2026, 10, 19, 12, 0, tzinfo=IST)
    positions = [
        PlanetPosition(planet="Sun", longitude=15.0, sign_index=0, retrograde=False),
        PlanetPosition(planet="Moon", longitude=45.0, sign_index=1, retrograde=False),
        PlanetPosition(planet="Mars", longitude=75.0, sign_index=2, retrograde=False),
        PlanetPosition(planet="Mercury", longitude=105.0, sign_index=3, retrograde=False),
        PlanetPosition(planet="Jupiter", longitude=135.0, sign_index=4, retrograde=False),
        PlanetPosition(planet="Venus", longitude=165.0, sign_index=5, retrograde=False),
        PlanetPosition(planet="Saturn", longitude=195.0, sign_index=6, retrograde=False),
        PlanetPosition(planet="Rahu", longitude=225.0, sign_index=7, retrograde=False),
        PlanetPosition(planet="Ketu", longitude=45.0, sign_index=1, retrograde=False),
    ]

    brief = strategist.run(
        "2026-10-19",
        [{"planet": p.planet, "sign": str(p.sign_index), "retrograde": p.retrograde} for p in positions],
        [],
    )

    draft = creator.run(brief, target_dt, positions, [])
    assert draft.title
    assert len(draft.full_script_md) > 500

    verdict = reviewer.run(draft, brief, revision_count=0)
    assert verdict.overall_score >= 8.0
    assert verdict.approved is True
    assert verdict.astrological_fidelity_score == 10.0


def test_telegram_notifier_headless():
    notifier = TelegramNotifier()
    # When unconfigured, it should safely return False without raising exceptions
    assert not notifier.is_configured
    assert notifier.send_message("Test message") is False
    assert notifier.notify_approval_request("2026-10-19", "Test Title", 13, 9.2, "Looks good") is False
