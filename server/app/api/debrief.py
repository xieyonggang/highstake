from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.models.debrief import Debrief
from app.models.session import Session
from app.models.transcript import TranscriptEntry
from app.schemas.debrief import CoachingItem, DebriefResponse, ScoreBreakdown
from app.schemas.transcript import TranscriptEntryResponse

router = APIRouter()


@router.get("/sessions/{session_id}/debrief", response_model=DebriefResponse)
async def get_debrief(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Debrief).where(Debrief.session_id == session_id)
    )
    debrief = result.scalar_one_or_none()
    if not debrief:
        raise HTTPException(status_code=404, detail="Debrief not found. Session may still be processing.")

    return DebriefResponse(
        id=debrief.id,
        session_id=debrief.session_id,
        scores=ScoreBreakdown(
            overall=debrief.overall_score,
            clarity=debrief.clarity_score,
            confidence=debrief.confidence_score,
            data_support=debrief.data_support_score,
            handling=debrief.handling_score,
            structure=debrief.structure_score,
        ),
        moderator_summary=debrief.moderator_summary,
        strengths=debrief.strengths,
        coaching_items=[CoachingItem(**item) for item in debrief.coaching_items],
    )


@router.get(
    "/sessions/{session_id}/transcript",
    response_model=list[TranscriptEntryResponse],
)
async def get_transcript(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Verify session exists
    session_result = await db.execute(select(Session).where(Session.id == session_id))
    if not session_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(TranscriptEntry)
        .where(TranscriptEntry.session_id == session_id)
        .order_by(TranscriptEntry.entry_index)
    )
    entries = result.scalars().all()
    return entries


@router.get("/sessions/{session_id}/recording")
async def get_recording(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.recording_key:
        raise HTTPException(status_code=404, detail="No recording available")

    from app.services.storage_service import StorageService

    storage = StorageService()
    url = await storage.get_signed_url(session.recording_key)
    return {"url": url}
