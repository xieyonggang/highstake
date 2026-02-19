from fastapi import APIRouter, HTTPException, UploadFile, File

from app.models.session import SessionStatus
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate
from app.services.session_store import (
    create_session as store_create,
    read_session as store_read,
    update_session as store_update,
    delete_session as store_delete,
)

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(payload: SessionCreate):
    session = store_create(payload.model_dump())
    return session


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    session = store_read(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(session_id: str, payload: SessionUpdate):
    updates = payload.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] is not None:
        try:
            updates["status"] = SessionStatus(updates["status"]).value
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {updates['status']}")

    session = store_update(session_id, updates)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str):
    if not store_delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")


@router.post("/{session_id}/recording")
async def upload_recording(
    session_id: str,
    recording: UploadFile = File(...),
):
    session = store_read(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.services.storage_service import StorageService

    storage = StorageService()
    recording_key = f"sessions/{session_id}/recordings/{recording.filename}"
    file_bytes = await recording.read()
    await storage.upload(recording_key, file_bytes, recording.content_type or "video/webm")

    store_update(session_id, {"recording_key": recording_key})
    return {"recording_key": recording_key}
