import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.base import async_session_factory
from app.models.debrief import Debrief
from app.models.session import Session, SessionStatus
from app.models.transcript import TranscriptEntry

logger = logging.getLogger(__name__)


async def finalize_session(session_id: str) -> None:
    """Generate scores and coaching for a completed session."""
    async with async_session_factory() as db:
        # Get session
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            logger.error(f"Session {session_id} not found for finalization")
            return

        # Get transcript entries
        entries_result = await db.execute(
            select(TranscriptEntry)
            .where(TranscriptEntry.session_id == session_id)
            .order_by(TranscriptEntry.entry_index)
        )
        entries = entries_result.scalars().all()

        transcript = [
            {
                "speaker": e.speaker,
                "speaker_name": e.speaker_name,
                "text": e.text,
                "start_time": e.start_time,
                "end_time": e.end_time,
                "slide_index": e.slide_index,
                "entry_type": e.entry_type,
            }
            for e in entries
        ]

        agent_questions = [t for t in transcript if t["entry_type"] == "question"]
        presenter_segments = [t for t in transcript if t["speaker"] == "presenter"]

        # Get exchange data if available
        from app.ws.events import session_exchange_data

        exchange_info = session_exchange_data.pop(session_id, {})
        exchanges = exchange_info.get("exchanges", [])
        unresolved = exchange_info.get("unresolved_challenges", [])

        # Calculate scores
        from app.services.scoring_engine import ScoringEngine

        scorer = ScoringEngine(
            transcript=transcript,
            agent_questions=agent_questions,
            slide_count=session.deck.total_slides if session.deck else 6,
            duration_secs=session.duration_secs or 0,
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

                deck_manifest = session.deck.manifest if session.deck else {}
                coaching_data = await generator.generate(
                    transcript=transcript,
                    scores=scores,
                    config={
                        "interaction_mode": session.interaction_mode,
                        "intensity": session.intensity,
                        "focus_areas": session.focus_areas,
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

        # Create debrief record
        debrief = Debrief(
            session_id=session.id,
            overall_score=scores["overall"],
            clarity_score=scores["clarity"],
            confidence_score=scores["confidence"],
            data_support_score=scores["data_support"],
            handling_score=scores["handling"],
            structure_score=scores["structure"],
            exchange_resilience_score=scores.get("exchange_resilience"),
            moderator_summary=moderator_summary,
            strengths=strengths,
            coaching_items=coaching_items,
            unresolved_challenges=unresolved if unresolved else None,
            exchange_data=exchange_info if exchange_info else None,
        )
        db.add(debrief)

        # Update session status
        session.status = SessionStatus.COMPLETE.value
        await db.commit()
        logger.info(f"Session {session_id} finalized with overall score {scores['overall']}")
