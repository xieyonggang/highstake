import os

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas.debrief import CoachingItem, DebriefResponse, ScoreBreakdown, UnresolvedChallenge
from app.schemas.transcript import TranscriptEntryResponse
from app.services.session_logger import SessionLogger

router = APIRouter()


@router.get("/sessions/{session_id}/debrief", response_model=DebriefResponse)
async def get_debrief(session_id: str):
    session_dir = os.path.join(settings.storage_dir, "sessions", session_id)
    data = SessionLogger.read_debrief(session_dir)
    if not data:
        raise HTTPException(status_code=404, detail="Debrief not found. Session may still be processing.")

    scores_raw = data.get("scores", {})
    challenges = None
    if data.get("unresolved_challenges"):
        challenges = [
            UnresolvedChallenge(**c) for c in data["unresolved_challenges"]
        ]

    return DebriefResponse(
        id=data.get("id", session_id),
        session_id=data.get("session_id", session_id),
        scores=ScoreBreakdown(
            overall=scores_raw.get("overall", 0),
            clarity=scores_raw.get("clarity", 0),
            confidence=scores_raw.get("confidence", 0),
            data_support=scores_raw.get("data_support", 0),
            handling=scores_raw.get("handling", 0),
            structure=scores_raw.get("structure", 0),
            exchange_resilience=scores_raw.get("exchange_resilience"),
        ),
        moderator_summary=data.get("moderator_summary", ""),
        strengths=data.get("strengths", []),
        coaching_items=[CoachingItem(**item) for item in data.get("coaching_items", [])],
        unresolved_challenges=challenges,
    )


@router.get(
    "/sessions/{session_id}/transcript",
    response_model=list[TranscriptEntryResponse],
)
async def get_transcript(session_id: str):
    session_dir = os.path.join(settings.storage_dir, "sessions", session_id)
    entries = SessionLogger.read_transcript_entries(session_dir)

    return [
        TranscriptEntryResponse(
            id=f"{session_id}-{e.get('entry_index', i)}",
            entry_index=e.get("entry_index", i),
            speaker=e.get("speaker", ""),
            speaker_name=e.get("speaker_name", ""),
            agent_role=e.get("agent_role"),
            text=e.get("text", ""),
            start_time=e.get("start_time", 0),
            end_time=e.get("end_time", 0),
            slide_index=e.get("slide_index"),
            entry_type=e.get("entry_type", ""),
            trigger_claim=e.get("trigger_claim"),
            audio_key=e.get("audio_key"),
        )
        for i, e in enumerate(entries)
    ]


@router.get("/sessions/{session_id}/recording")
async def get_recording(session_id: str):
    rec_dir = os.path.join(settings.storage_dir, "sessions", session_id, "recordings")
    if not os.path.isdir(rec_dir):
        raise HTTPException(status_code=404, detail="No recording available")
    files = os.listdir(rec_dir)
    if not files:
        raise HTTPException(status_code=404, detail="No recording available")
    return {"url": f"/api/files/sessions/{session_id}/recordings/{files[0]}"}
