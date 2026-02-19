import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.schemas.deck import DeckManifest

logger = logging.getLogger(__name__)

router = APIRouter()


async def _extract_and_store_claims(session_id: str, deck_id: str, manifest_data: dict) -> None:
    """Background task: extract claims from deck and write claims.json to disk."""
    from app.config import settings

    if not settings.gemini_api_key:
        return

    try:
        from app.services.llm_client import LLMClient
        from app.services.claim_extractor import extract_claims_from_deck
        from app.services.storage_service import StorageService

        llm = LLMClient(settings.gemini_api_key)
        claims = await extract_claims_from_deck(llm, manifest_data)

        storage = StorageService()
        claims_key = f"sessions/{session_id}/decks/{deck_id}/claims.json"
        await storage.upload(claims_key, json.dumps(claims).encode(), "application/json")
        logger.info(
            f"Claims extracted and stored for deck {deck_id}: "
            f"{sum(len(v) for v in claims.values())} claims"
        )
    except Exception as e:
        logger.error(f"Background claim extraction failed for deck {deck_id}: {e}")


@router.post("/upload", response_model=DeckManifest, status_code=201)
async def upload_deck(
    file: UploadFile = File(...),
    session_id: str | None = None,
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    filename_lower = file.filename.lower()
    if not filename_lower.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported. Please export your PPTX to PDF first.")

    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")

    from app.services.deck_parser import DeckParserService

    parser = DeckParserService()
    manifest_data = await parser.parse_and_store(
        file_bytes, file.filename, session_id=session_id
    )

    # Kick off background claim extraction (non-blocking)
    if session_id:
        asyncio.create_task(
            _extract_and_store_claims(session_id, manifest_data["id"], manifest_data)
        )

    return manifest_data
