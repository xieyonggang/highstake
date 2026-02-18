from typing import Optional

from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    overall: int
    clarity: int
    confidence: int
    data_support: int
    handling: int
    structure: int
    exchange_resilience: Optional[int] = None


class CoachingItem(BaseModel):
    area: str
    priority: str  # "high", "medium", "low"
    detail: str
    timestamp_ref: Optional[float] = None


class UnresolvedChallenge(BaseModel):
    agent_id: str
    question: str
    target_claim: Optional[str] = None
    slide_index: Optional[int] = None
    outcome: str
    turn_count: int


class DebriefResponse(BaseModel):
    id: str
    session_id: str
    scores: ScoreBreakdown
    moderator_summary: str
    strengths: list[str]
    coaching_items: list[CoachingItem]
    unresolved_challenges: Optional[list[UnresolvedChallenge]] = None

    model_config = {"from_attributes": True}
