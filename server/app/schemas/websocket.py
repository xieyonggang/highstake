from typing import Optional

from pydantic import BaseModel


class AgentQuestionEvent(BaseModel):
    agent_id: str
    text: str
    audio_url: Optional[str] = None
    slide_ref: Optional[int] = None


class ModeratorMessageEvent(BaseModel):
    text: str
    audio_url: Optional[str] = None


class SessionStateEvent(BaseModel):
    state: str  # "presenting", "q_and_a", "ending"


class SlideChangeEvent(BaseModel):
    slide_index: int


class SessionEndedEvent(BaseModel):
    session_id: str
    debrief_ready: bool = False
