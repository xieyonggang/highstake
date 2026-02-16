import io
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deck import Deck, Slide

logger = logging.getLogger(__name__)


class DeckParserService:
    async def parse_and_store(
        self,
        file_bytes: bytes,
        filename: str,
        db: AsyncSession,
    ) -> dict:
        """Full pipeline: parse file, generate thumbnails, store in DB."""
        filename_lower = filename.lower()
        is_pptx = filename_lower.endswith(".pptx")
        is_pdf = filename_lower.endswith(".pdf")

        if not (is_pptx or is_pdf):
            raise ValueError("Unsupported file format. Only PPTX and PDF are supported.")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / filename
            file_path.write_bytes(file_bytes)

            if is_pptx:
                slides_data = self._parse_pptx(file_path)
            else:
                slides_data = self._parse_pdf(file_path)

            # Generate thumbnails
            thumbnails = self._generate_thumbnails(file_path, tmpdir_path, is_pptx)

            # Upload original file to storage
            from app.services.storage_service import StorageService

            storage = StorageService()
            deck_id = uuid.uuid4()
            file_key = f"decks/{deck_id}/{filename}"
            await storage.upload(file_key, file_bytes, self._content_type(filename))

            # Upload thumbnails
            for i, thumb_bytes in enumerate(thumbnails):
                if thumb_bytes:
                    thumb_key = f"decks/{deck_id}/thumbnails/{i}.png"
                    await storage.upload(thumb_key, thumb_bytes, "image/png")
                    slides_data[i]["thumbnail_key"] = thumb_key

            # Create DB records
            deck = Deck(
                id=deck_id,
                filename=filename,
                file_size_bytes=len(file_bytes),
                file_key=file_key,
                total_slides=len(slides_data),
                manifest={
                    "id": str(deck_id),
                    "filename": filename,
                    "totalSlides": len(slides_data),
                    "slides": slides_data,
                },
            )
            db.add(deck)

            for slide_data in slides_data:
                slide = Slide(
                    deck_id=deck_id,
                    slide_index=slide_data["index"],
                    title=slide_data.get("title"),
                    subtitle=slide_data.get("subtitle"),
                    body_text=slide_data.get("body_text"),
                    notes=slide_data.get("notes"),
                    has_chart=slide_data.get("has_chart", False),
                    has_table=slide_data.get("has_table", False),
                    thumbnail_key=slide_data.get("thumbnail_key"),
                )
                db.add(slide)

            await db.flush()
            await db.refresh(deck)

            return {
                "id": deck_id,
                "filename": filename,
                "total_slides": len(slides_data),
                "slides": [
                    {
                        "index": s["index"],
                        "title": s.get("title"),
                        "subtitle": s.get("subtitle"),
                        "body_text": s.get("body_text"),
                        "notes": s.get("notes"),
                        "has_chart": s.get("has_chart", False),
                        "has_table": s.get("has_table", False),
                        "thumbnail_url": (
                            f"/api/decks/{deck_id}/slides/{s['index']}"
                            if s.get("thumbnail_key")
                            else None
                        ),
                    }
                    for s in slides_data
                ],
                "created_at": deck.created_at,
            }

    def _parse_pptx(self, file_path: Path) -> list[dict]:
        """Extract text, titles, notes from PPTX."""
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        prs = Presentation(str(file_path))
        slides_data = []

        for i, slide in enumerate(prs.slides):
            title = ""
            subtitle = ""
            body_parts = []
            has_chart = False
            has_table = False
            notes = ""

            # Extract title
            if slide.shapes.title:
                title = slide.shapes.title.text.strip()

            for shape in slide.shapes:
                # Check shape types
                if shape.shape_type == MSO_SHAPE_TYPE.CHART:
                    has_chart = True
                elif shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                    has_table = True
                    # Extract table text
                    if hasattr(shape, "table"):
                        for row in shape.table.rows:
                            row_text = " | ".join(cell.text.strip() for cell in row.cells)
                            if row_text.strip():
                                body_parts.append(row_text)

                # Extract text from text frames
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            if shape == slide.shapes.title:
                                continue  # Already captured
                            elif not subtitle and shape.shape_id != slide.shapes.title.shape_id if slide.shapes.title else True:
                                # First non-title text block could be subtitle
                                if not subtitle and len(body_parts) == 0:
                                    subtitle = text
                                else:
                                    body_parts.append(text)

            # Extract speaker notes
            if slide.has_notes_slide:
                notes_frame = slide.notes_slide.notes_text_frame
                if notes_frame:
                    notes = notes_frame.text.strip()

            slides_data.append({
                "index": i,
                "title": title,
                "subtitle": subtitle,
                "body_text": "\n".join(body_parts),
                "notes": notes,
                "has_chart": has_chart,
                "has_table": has_table,
            })

        return slides_data

    def _parse_pdf(self, file_path: Path) -> list[dict]:
        """Extract text from PDF pages."""
        import fitz  # PyMuPDF

        doc = fitz.open(str(file_path))
        slides_data = []

        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            title = lines[0] if lines else f"Page {i + 1}"
            subtitle = lines[1] if len(lines) > 1 else ""
            body_text = "\n".join(lines[2:]) if len(lines) > 2 else ""

            slides_data.append({
                "index": i,
                "title": title,
                "subtitle": subtitle,
                "body_text": body_text,
                "notes": "",
                "has_chart": False,
                "has_table": False,
            })

        doc.close()
        return slides_data

    def _generate_thumbnails(
        self,
        file_path: Path,
        output_dir: Path,
        is_pptx: bool,
    ) -> list[Optional[bytes]]:
        """Generate thumbnail images for each slide/page."""
        thumbnails = []

        if is_pptx:
            # For PPTX, we generate text-based placeholder thumbnails
            # Full PPTX rendering requires LibreOffice or similar
            try:
                from pptx import Presentation
                from PIL import Image, ImageDraw, ImageFont

                prs = Presentation(str(file_path))
                for i, slide in enumerate(prs.slides):
                    thumb = self._create_text_thumbnail(
                        title=slide.shapes.title.text.strip() if slide.shapes.title else f"Slide {i + 1}",
                        index=i,
                    )
                    thumbnails.append(thumb)
            except Exception as e:
                logger.warning(f"Failed to generate PPTX thumbnails: {e}")

        else:
            # For PDF, use PyMuPDF to render pages
            try:
                import fitz

                doc = fitz.open(str(file_path))
                for page in doc:
                    mat = fitz.Matrix(2, 2)  # 2x zoom
                    pix = page.get_pixmap(matrix=mat)
                    thumbnails.append(pix.tobytes("png"))
                doc.close()
            except Exception as e:
                logger.warning(f"Failed to generate PDF thumbnails: {e}")

        return thumbnails

    def _create_text_thumbnail(self, title: str, index: int) -> bytes:
        """Create a simple text-based thumbnail for a PPTX slide."""
        from PIL import Image, ImageDraw, ImageFont

        width, height = 1280, 720
        img = Image.new("RGB", (width, height), color=(30, 30, 40))
        draw = ImageDraw.Draw(img)

        # Draw slide number
        draw.text((40, 30), f"Slide {index + 1}", fill=(100, 100, 140))

        # Draw title
        # Use default font (PIL built-in)
        title_wrapped = title[:60]
        draw.text((40, 80), title_wrapped, fill=(220, 220, 240))

        # Draw border
        draw.rectangle([0, 0, width - 1, height - 1], outline=(60, 60, 80), width=2)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _content_type(self, filename: str) -> str:
        if filename.lower().endswith(".pptx"):
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif filename.lower().endswith(".pdf"):
            return "application/pdf"
        return "application/octet-stream"
