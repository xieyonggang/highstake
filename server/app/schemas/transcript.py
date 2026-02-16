from typing import Optional

from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    """Real-time transcript segment from STT."""

    type: str  # "interim" or "final"
    text: str
    start_time: float
    end_time: float
    confidence: float = 0.0
    is_final: bool = False


class TranscriptEntryResponse(BaseModel):
    id: str
    entry_index: int
    speaker: str
    speaker_name: str
    agent_role: Optional[str]
    text: str
    start_time: float
    end_time: float
    slide_index: Optional[int]
    entry_type: str
    trigger_claim: Optional[str]
    audio_key: Optional[str]

    model_config = {"from_attributes": True}
