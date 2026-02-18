"""Session context dataclasses for multi-turn exchanges and presenter tracking."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ExchangeOutcome(str, Enum):
    SATISFIED = "satisfied"
    FOLLOW_UP = "follow_up"
    ESCALATE = "escalate"
    MODERATOR_INTERVENED = "moderator_intervened"
    TURN_LIMIT = "turn_limit"
    TIMEOUT = "timeout"


class SessionState(str, Enum):
    PRESENTING = "presenting"
    QA_TRIGGER = "qa_trigger"
    EXCHANGE = "exchange"
    RESOLVING = "resolving"


@dataclass
class ExchangeTurn:
    speaker: str  # "agent" or "presenter"
    text: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class CandidateQuestion:
    agent_id: str
    text: str
    target_claim: Optional[str] = None
    slide_index: Optional[int] = None
    relevance_score: float = 0.0
    audio_url: Optional[str] = None


@dataclass
class Exchange:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    question_text: str = ""
    target_claim: Optional[str] = None
    slide_index: int = 0
    turns: list[ExchangeTurn] = field(default_factory=list)
    outcome: Optional[ExchangeOutcome] = None
    started_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    evaluation_reasoning: Optional[str] = None

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def presenter_turn_count(self) -> int:
        return sum(1 for t in self.turns if t.speaker == "presenter")

    @property
    def agent_turn_count(self) -> int:
        return sum(1 for t in self.turns if t.speaker == "agent")

    @property
    def is_resolved(self) -> bool:
        return self.outcome is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "question_text": self.question_text,
            "target_claim": self.target_claim,
            "slide_index": self.slide_index,
            "turns": [
                {"speaker": t.speaker, "text": t.text, "timestamp": t.timestamp}
                for t in self.turns
            ],
            "outcome": self.outcome.value if self.outcome else None,
            "started_at": self.started_at,
            "resolved_at": self.resolved_at,
            "evaluation_reasoning": self.evaluation_reasoning,
        }


@dataclass
class PresenterProfile:
    """Tracks observed response patterns for adaptive questioning."""
    response_patterns: list[str] = field(default_factory=list)
    data_readiness: str = "unknown"  # "strong", "moderate", "weak", "unknown"
    behavioral_notes: list[str] = field(default_factory=list)
    recommended_strategy: str = "standard"  # "push_harder", "standard", "supportive"

    def to_text(self) -> str:
        parts = []
        if self.response_patterns:
            parts.append("Observed response patterns:")
            for p in self.response_patterns[-5:]:
                parts.append(f"  - {p}")
        if self.data_readiness != "unknown":
            parts.append(f"Data readiness: {self.data_readiness}")
        if self.behavioral_notes:
            parts.append("Behavioral notes:")
            for n in self.behavioral_notes[-5:]:
                parts.append(f"  - {n}")
        if self.recommended_strategy != "standard":
            parts.append(f"Recommended approach: {self.recommended_strategy}")
        return "\n".join(parts) if parts else ""


@dataclass
class AgentSessionContext:
    """Per-agent mutable context accumulated during a session."""
    agent_id: str
    exchanges: list[Exchange] = field(default_factory=list)
    presenter_profile: PresenterProfile = field(default_factory=PresenterProfile)
    challenged_claims: list[str] = field(default_factory=list)

    @property
    def total_questions(self) -> int:
        return len(self.exchanges)

    @property
    def satisfied_count(self) -> int:
        return sum(
            1 for e in self.exchanges
            if e.outcome == ExchangeOutcome.SATISFIED
        )

    @property
    def unresolved_exchanges(self) -> list[Exchange]:
        return [
            e for e in self.exchanges
            if e.outcome in (
                ExchangeOutcome.MODERATOR_INTERVENED,
                ExchangeOutcome.TURN_LIMIT,
            )
        ]


@dataclass
class SessionContext:
    """Top-level session context holding all agent contexts and global state."""
    session_id: str
    state: SessionState = SessionState.PRESENTING
    active_exchange: Optional[Exchange] = None
    agent_contexts: dict[str, AgentSessionContext] = field(default_factory=dict)
    completed_exchanges: list[Exchange] = field(default_factory=list)
    claims_by_slide: dict[int, list[dict]] = field(default_factory=dict)

    def get_agent_context(self, agent_id: str) -> AgentSessionContext:
        if agent_id not in self.agent_contexts:
            self.agent_contexts[agent_id] = AgentSessionContext(agent_id=agent_id)
        return self.agent_contexts[agent_id]

    @property
    def all_exchanges(self) -> list[Exchange]:
        return self.completed_exchanges

    @property
    def unresolved_challenges(self) -> list[dict]:
        challenges = []
        for exchange in self.completed_exchanges:
            if exchange.outcome in (
                ExchangeOutcome.MODERATOR_INTERVENED,
                ExchangeOutcome.TURN_LIMIT,
            ):
                challenges.append({
                    "agent_id": exchange.agent_id,
                    "question": exchange.question_text,
                    "target_claim": exchange.target_claim,
                    "slide_index": exchange.slide_index,
                    "outcome": exchange.outcome.value,
                    "turn_count": exchange.turn_count,
                })
        return challenges

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "exchanges": [e.to_dict() for e in self.completed_exchanges],
            "unresolved_challenges": self.unresolved_challenges,
        }
