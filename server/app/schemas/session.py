from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionCreate(BaseModel):
    interaction_mode: str
    intensity: str
    agents: list[str] = ["skeptic", "analyst", "contrarian"]
    focus_areas: list[str] = []
    deck_id: Optional[str] = None


class SessionUpdate(BaseModel):
    status: Optional[str] = None
    interaction_mode: Optional[str] = None
    intensity: Optional[str] = None
    agents: Optional[list[str]] = None
    deck_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_secs: Optional[int] = None


class SessionResponse(BaseModel):
    id: str
    status: str
    interaction_mode: str
    intensity: str
    agents: list[str]
    focus_areas: list[str]
    deck_id: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_secs: Optional[int]
    recording_key: Optional[str]
    created_at: datetime
    updated_at: datetime

