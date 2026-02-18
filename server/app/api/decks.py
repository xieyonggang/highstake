import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.models.deck import Deck, Slide
from app.schemas.deck import DeckManifest, SlideData

logger = logging.getLogger(__name__)

router = APIRouter()


async def _extract_and_store_claims(deck_id: str, manifest_data: dict) -> None:
    """Background task: extract claims from deck and persist to DB."""
    from app.config import settings

    if not settings.gemini_api_key:
        return

    try:
        from app.services.llm_client import LLMClient
        from app.services.claim_extractor import extract_claims_from_deck
        from app.models.base import async_session_factory

        llm = LLMClient(settings.gemini_api_key)
        claims = await extract_claims_from_deck(llm, manifest_data)

        async with async_session_factory() as db:
            result = await db.execute(
                select(Deck).where(Deck.id == deck_id)
            )
            deck = result.scalar_one_or_none()
            if deck:
                deck.claims_json = claims
                await db.commit()
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
    db: AsyncSession = Depends(get_db),
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

    # Import here to avoid circular imports during startup
    from app.services.deck_parser import DeckParserService

    parser = DeckParserService()
    manifest_data = await parser.parse_and_store(
        file_bytes, file.filename, db, session_id=session_id
    )

    # Kick off background claim extraction (non-blocking)
    asyncio.create_task(
        _extract_and_store_claims(manifest_data["id"], manifest_data)
    )

    return manifest_data


@router.get("/{deck_id}", response_model=DeckManifest)
async def get_deck(
    deck_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Deck).where(Deck.id == deck_id))
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    slides_result = await db.execute(
        select(Slide).where(Slide.deck_id == deck_id).order_by(Slide.slide_index)
    )
    slides = slides_result.scalars().all()

    return DeckManifest(
        id=deck.id,
        filename=deck.filename,
        total_slides=deck.total_slides,
        slides=[
            SlideData(
                index=s.slide_index,
                title=s.title,
                subtitle=s.subtitle,
                body_text=s.body_text,
                notes=s.notes,
                has_chart=s.has_chart,
                has_table=s.has_table,
                thumbnail_url=f"/api/decks/{deck_id}/slides/{s.slide_index}" if s.thumbnail_key else None,
            )
            for s in slides
        ],
        created_at=deck.created_at,
    )


@router.get("/{deck_id}/slides/{index}")
async def get_slide_thumbnail(
    deck_id: str,
    index: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Slide).where(Slide.deck_id == deck_id, Slide.slide_index == index)
    )
    slide = result.scalar_one_or_none()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    if not slide.thumbnail_key:
        raise HTTPException(status_code=404, detail="No thumbnail available")

    from app.services.storage_service import StorageService

    storage = StorageService()
    url = await storage.get_url(slide.thumbnail_key)
    return RedirectResponse(url=url)
