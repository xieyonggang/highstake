"""Session-scoped async event bus for decoupling agent communication.

Each session gets its own EventBus instance. Agents and the coordinator
subscribe to event types and receive non-blocking delivery via
asyncio.create_task.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    TRANSCRIPT_UPDATE = "transcript_update"
    TRANSCRIPT_INTERIM = "transcript_interim"
    SLIDE_CHANGED = "slide_changed"
    EXCHANGE_STARTED = "exchange_started"
    EXCHANGE_RESOLVED = "exchange_resolved"
    AGENT_SPOKE = "agent_spoke"
    HAND_RAISED = "hand_raised"
    HAND_LOWERED = "hand_lowered"
    AGENT_CALLED_ON = "agent_called_on"
    SESSION_ENDING = "session_ending"
    CLAIMS_READY = "claims_ready"


@dataclass
class Event:
    type: EventType
    data: dict
    timestamp: float = field(default_factory=time.time)
    source: str = ""  # "system", "moderator", or agent_id


class EventBus:
    """In-process async event bus for a single session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._subscribers: dict[EventType, list[Callable[[Event], Awaitable[None]]]] = {}
        self._history: list[Event] = []
        self._max_history = 200

    def subscribe(self, event_type: EventType, callback: Callable[[Event], Awaitable[None]]):
        self._subscribers.setdefault(event_type, []).append(callback)

    def subscribe_all(self, callback: Callable[[Event], Awaitable[None]]):
        """Subscribe to all event types."""
        for et in EventType:
            self.subscribe(et, callback)

    async def publish(self, event: Event):
        """Publish event to all subscribers. Each callback runs as its own task."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        callbacks = self._subscribers.get(event.type, [])
        for cb in callbacks:
            try:
                asyncio.create_task(cb(event))
            except Exception as e:
                logger.error(
                    f"EventBus [{self.session_id}]: error scheduling "
                    f"subscriber for {event.type}: {e}"
                )

    def get_recent_events(
        self, event_type: EventType | None = None, limit: int = 50
    ) -> list[Event]:
        if event_type:
            return [e for e in self._history if e.type == event_type][-limit:]
        return self._history[-limit:]
