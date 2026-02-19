import json
import logging
import os

from app.config import settings
from app.services.session_store import read_session, update_session
from app.services.session_logger import SessionLogger

logger = logging.getLogger(__name__)


async def finalize_session(session_id: str) -> None:
    """Generate scores and coaching for a completed session."""
    session = read_session(session_id)
    if not session:
        logger.error(f"Session {session_id} not found for finalization")
        return

    # Get transcript entries from session folder
    session_dir = os.path.join(settings.storage_dir, "sessions", session_id)
    transcript = SessionLogger.read_transcript_entries(session_dir)

    agent_questions = [t for t in transcript if t["entry_type"] == "question"]
    presenter_segments = [t for t in transcript if t["speaker"] == "presenter"]

    # Get exchange data if available
    from app.ws.events import session_exchange_data

    exchange_info = session_exchange_data.pop(session_id, {})
    exchanges = exchange_info.get("exchanges", [])
    unresolved = exchange_info.get("unresolved_challenges", [])

    # Read deck manifest from file
    deck_manifest = {}
    slide_count = 6
    if session.get("deck_id"):
        manifest_path = os.path.join(
            settings.storage_dir, "sessions", session_id,
            "decks", session["deck_id"], "manifest.json",
        )
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                deck_manifest = json.load(f)
            slide_count = deck_manifest.get("totalSlides", 6)

    # Calculate scores
    from app.services.scoring_engine import ScoringEngine

    scorer = ScoringEngine(
        transcript=transcript,
        agent_questions=agent_questions,
        slide_count=slide_count,
        duration_secs=session.get("duration_secs") or 0,
        exchanges=exchanges,
    )
    scores = scorer.calculate_all_scores()

    # Generate coaching
    moderator_summary = "Session analysis is being generated."
    strengths = []
    coaching_items = []

    if settings.gemini_api_key:
        try:
            from app.services.llm_client import LLMClient
            from app.services.coaching_generator import CoachingGenerator

            llm = LLMClient(settings.gemini_api_key)
            generator = CoachingGenerator(llm)

            coaching_data = await generator.generate(
                transcript=transcript,
                scores=scores,
                config={
                    "interaction_mode": session["interaction_mode"],
                    "intensity": session["intensity"],
                    "focus_areas": session.get("focus_areas", []),
                },
                deck_manifest=deck_manifest,
            )
            moderator_summary = coaching_data.get("moderator_summary", moderator_summary)
            strengths = coaching_data.get("strengths", [])
            coaching_items = coaching_data.get("coaching_items", [])
        except Exception as e:
            logger.error(f"Failed to generate coaching for session {session_id}: {e}")
            moderator_summary = (
                "Thank you for your presentation today. The scoring analysis has been completed, "
                "but the detailed coaching summary could not be generated at this time. "
                "Please review the individual scores for insights on your performance."
            )

    # Write debrief to session folder
    session_logger = SessionLogger(session_id, settings.storage_dir)
    debrief_data = {
        "id": session_id,
        "session_id": session_id,
        "scores": scores,
        "moderator_summary": moderator_summary,
        "strengths": strengths,
        "coaching_items": coaching_items,
        "unresolved_challenges": unresolved if unresolved else None,
        "exchange_data": exchange_info if exchange_info else None,
    }
    await session_logger.write_debrief(debrief_data)

    # Update session status
    update_session(session_id, {"status": "complete"})
    logger.info(f"Session {session_id} finalized with overall score {scores['overall']}")
