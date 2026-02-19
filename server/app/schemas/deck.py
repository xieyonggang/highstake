from typing import Optional

from pydantic import BaseModel


class SlideData(BaseModel):
    index: int
    title: Optional[str] = None
    subtitle: Optional[str] = None
    body_text: Optional[str] = None
    notes: Optional[str] = None
    has_chart: bool = False
    has_table: bool = False
    thumbnail_url: Optional[str] = None


class DeckManifest(BaseModel):
    id: str
    filename: str
    total_slides: int
    slides: list[SlideData]
