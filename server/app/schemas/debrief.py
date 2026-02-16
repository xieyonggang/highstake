from typing import Optional

from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    overall: int
    clarity: int
    confidence: int
    data_support: int
    handling: int
    structure: int


class CoachingItem(BaseModel):
    area: str
    priority: str  # "high", "medium", "low"
    detail: str
    timestamp_ref: Optional[float] = None


class DebriefResponse(BaseModel):
    id: str
    session_id: str
    scores: ScoreBreakdown
    moderator_summary: str
    strengths: list[str]
    coaching_items: list[CoachingItem]

    model_config = {"from_attributes": True}
