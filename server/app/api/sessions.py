from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.models.session import Session, SessionStatus
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    session = Session(
        interaction_mode=payload.interaction_mode,
        intensity=payload.intensity,
        agents=payload.agents,
        focus_areas=payload.focus_areas,
        deck_id=payload.deck_id,
        status=SessionStatus.CONFIGURING.value,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    payload: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.status is not None:
        try:
            session.status = SessionStatus(payload.status).value
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")
    if payload.interaction_mode is not None:
        session.interaction_mode = payload.interaction_mode
    if payload.intensity is not None:
        session.intensity = payload.intensity
    if payload.agents is not None:
        session.agents = payload.agents
    if payload.deck_id is not None:
        session.deck_id = payload.deck_id
    if payload.started_at is not None:
        session.started_at = payload.started_at
    if payload.ended_at is not None:
        session.ended_at = payload.ended_at
    if payload.duration_secs is not None:
        session.duration_secs = payload.duration_secs

    await db.flush()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)


@router.post("/{session_id}/recording")
async def upload_recording(
    session_id: str,
    recording: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.services.storage_service import StorageService

    storage = StorageService()
    recording_key = f"sessions/{session_id}/recordings/{recording.filename}"
    file_bytes = await recording.read()
    await storage.upload(recording_key, file_bytes, recording.content_type or "video/webm")

    session.recording_key = recording_key
    await db.flush()

    return {"recording_key": recording_key}
