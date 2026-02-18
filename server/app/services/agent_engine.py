"""Session coordinator (formerly AgentEngine).

Manages the moderator, hand-raise queue, exchange lifecycle, and spawns
autonomous AgentRunner tasks. Does NOT generate questions — agents do that
independently.
"""

import asyncio
import glob
import logging
import os
import random
import time
from typing import Optional

from app.services.agent_prompts import (
    AGENT_NAMES,
    AGENT_ROLES,
    AGENT_TITLES,
)
from app.services.agent_runner import AgentRunner
from app.services.context_manager import ContextManager
from app.services.event_bus import Event, EventBus, EventType
from app.services.llm_client import LLMClient
from app.services.session_context import (
    CandidateQuestion,
    Exchange,
    ExchangeOutcome,
    ExchangeTurn,
    SessionContext,
    SessionState,
)
from app.services.filler_service import FillerService
from app.services.session_logger import SessionLogger
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)


class SessionCoordinator:
    """Coordinates the session: moderator, hand-raise queue, exchanges.

    Backward-compatible alias: AgentEngine → SessionCoordinator.
    The external API (on_transcript_segment, on_slide_change, initialize_claims)
    is the same so ws/events.py works unchanged.
    """

    def __init__(
        self,
        session_id: str,
        config: dict,
        deck_manifest: dict,
        llm_client: LLMClient,
        tts_service: TTSService,
        emit_callback,
    ):
        self.session_id = session_id
        self.config = config
        self.deck_manifest = deck_manifest
        self.llm = llm_client
        self.tts = tts_service
        self.emit = emit_callback

        # Event bus — shared by all agents
        self.event_bus = EventBus(session_id)

        # Context (for moderator and shared state)
        self.context = ContextManager()
        self.current_slide = 0
        self.session_start_time: float = time.time()

        # Session context — exchanges, claims, agent contexts
        self.session_context = SessionContext(session_id=session_id)
        self.claims_by_slide: dict[int, list[dict]] = {}

        # Agent runners
        self.runners: dict[str, AgentRunner] = {}
        self.active_agents: list[str] = config.get(
            "agents", ["skeptic", "analyst", "contrarian"]
        )

        # Hand-raise queue: (agent_id, CandidateQuestion, timestamp)
        self._hand_raise_queue: list[tuple[str, CandidateQuestion, float]] = []
        self._hand_raise_lock = asyncio.Lock()

        # Limit concurrent LLM calls across all agents in this session
        self._llm_semaphore = asyncio.Semaphore(2)

        # Exchange management
        self._exchange_timeout_task: Optional[asyncio.Task] = None
        self._exchange_timeout_secs: int = 45
        self._turn_limits = {"friendly": 2, "moderate": 3, "adversarial": 4}

        # Filler audio service
        self.filler_service = FillerService()

        # Post-exchange cooldown
        self._last_exchange_resolved_at: float = 0
        self._post_exchange_pause_secs: float = 5.0

        # Exchange response accumulation — wait for presenter to finish speaking
        self._exchange_response_buffer: list[str] = []
        self._exchange_response_debounce: Optional[asyncio.Task] = None
        self._exchange_response_pause_secs: float = 3.0  # wait 3s of silence
        self._exchange_min_words: int = 8  # need at least ~8 words

        # Time warnings
        self._time_warning_80_sent = False
        self._time_warning_90_sent = False

        # Moderator loop task
        self._moderator_task: Optional[asyncio.Task] = None
        self._transcript_entry_count: int = 0
        self._running = False

        # Session debug logger
        from app.config import settings as app_settings
        self.session_logger = SessionLogger(session_id, app_settings.storage_dir)

    def _elapsed_seconds(self) -> float:
        return time.time() - self.session_start_time

    async def _log_bus_event(self, event: Event) -> None:
        """Log every event bus event to timeline.md."""
        await self.session_logger.log_timeline_event(
            event.type.value, event.data, event.source
        )

    # --- Lifecycle ---

    async def start(self) -> None:
        """Start all agent runners and the moderator loop."""
        self._running = True

        # Log session config and copy agent templates into session folder
        await self.session_logger.log_session_config(
            self.config, self.deck_manifest, self.active_agents
        )

        # Subscribe coordinator to hand-raise events
        self.event_bus.subscribe(EventType.HAND_RAISED, self._on_hand_raised)
        self.event_bus.subscribe(EventType.HAND_LOWERED, self._on_hand_lowered)

        # Subscribe logger to ALL events for timeline
        self.event_bus.subscribe_all(self._log_bus_event)

        # Spawn agent runners
        for i, agent_id in enumerate(self.active_agents):
            agent_ctx = self.session_context.get_agent_context(agent_id)
            runner = AgentRunner(
                agent_id=agent_id,
                agent_index=i,
                session_id=self.session_id,
                config=self.config,
                deck_manifest=self.deck_manifest,
                claims_by_slide=self.claims_by_slide,
                event_bus=self.event_bus,
                llm_client=self.llm,
                tts_service=self.tts,
                emit_callback=self.emit,
                session_context=agent_ctx,
                llm_semaphore=self._llm_semaphore,
                session_logger=self.session_logger,
            )
            self.runners[agent_id] = runner
            await runner.start()

        # Start moderator loop
        self._moderator_task = asyncio.create_task(self._moderator_loop())
        logger.info(
            f"SessionCoordinator started for {self.session_id} "
            f"with {len(self.runners)} agents"
        )

    async def stop(self) -> None:
        """Stop all runners and the moderator loop."""
        self._running = False

        # Signal session ending to all agents
        await self.event_bus.publish(
            Event(type=EventType.SESSION_ENDING, data={}, source="system")
        )

        for runner in self.runners.values():
            await runner.stop()

        self._cancel_exchange_timer()

        if self._moderator_task:
            self._moderator_task.cancel()
            try:
                await self._moderator_task
            except asyncio.CancelledError:
                pass

        logger.info(f"SessionCoordinator stopped for {self.session_id}")

    # --- External API (called from ws/events.py) ---

    async def initialize_claims(self) -> None:
        """Extract claims from deck slides in background."""
        if not self.deck_manifest.get("slides"):
            return
        try:
            from app.services.claim_extractor import extract_claims_from_deck

            self.claims_by_slide = await extract_claims_from_deck(
                self.llm, self.deck_manifest
            )
            self.session_context.claims_by_slide = self.claims_by_slide
            logger.info(f"Claims initialized for session {self.session_id}")
            await self.session_logger.log_claims(self.claims_by_slide)

            # Broadcast to all agents
            await self.event_bus.publish(
                Event(
                    type=EventType.CLAIMS_READY,
                    data={"claims_by_slide": self.claims_by_slide},
                    source="system",
                )
            )
        except Exception as e:
            logger.warning(f"Claim extraction failed: {e}")

    async def on_transcript_segment(self, segment: dict) -> None:
        """Called when a new transcript segment arrives from STT."""
        self.context.add_segment(segment)

        # Log and store final presenter segments
        if segment.get("is_final") and segment.get("text", "").strip():
            await self.session_logger.log_transcript(segment)
            await self._store_transcript_entry(
                agent_id="presenter",
                text=segment["text"],
                entry_type="presenter",
            )

        # If in active exchange, route presenter response to exchange handler
        if (
            self.session_context.state == SessionState.EXCHANGE
            and self.session_context.active_exchange
            and segment.get("is_final")
        ):
            await self._handle_exchange_response(segment)

        # Broadcast to all agents via event bus
        if segment.get("is_final"):
            await self.event_bus.publish(
                Event(
                    type=EventType.TRANSCRIPT_UPDATE,
                    data=segment,
                    source="presenter",
                )
            )
        else:
            await self.event_bus.publish(
                Event(
                    type=EventType.TRANSCRIPT_INTERIM,
                    data=segment,
                    source="presenter",
                )
            )

    async def on_slide_change(self, slide_index: int) -> None:
        """Called when the presenter advances slides."""
        self.current_slide = slide_index

        # Time warnings
        warning = self._check_time_warnings()
        if warning:
            await self._emit_moderator(warning)

        # Broadcast to all agents
        await self.event_bus.publish(
            Event(
                type=EventType.SLIDE_CHANGED,
                data={"slide_index": slide_index},
                source="system",
            )
        )

    # --- Hand-raise queue management ---

    async def _on_hand_raised(self, event: Event) -> None:
        """Agent raised hand — add to queue."""
        agent_id = event.data.get("agent_id")
        question = event.data.get("question")
        if not agent_id:
            return

        async with self._hand_raise_lock:
            # Don't add if already in queue
            if any(aid == agent_id for aid, _, _ in self._hand_raise_queue):
                return
            self._hand_raise_queue.append(
                (agent_id, question, time.time())
            )
            logger.info(
                f"Hand-raise queue: {[a for a, _, _ in self._hand_raise_queue]}"
            )

        # Emit queue update to frontend
        await self._emit_queue_update()

    async def _on_hand_lowered(self, event: Event) -> None:
        """Agent lowered hand — remove from queue."""
        agent_id = event.data.get("agent_id")
        if not agent_id:
            return

        async with self._hand_raise_lock:
            self._hand_raise_queue = [
                (aid, q, t)
                for aid, q, t in self._hand_raise_queue
                if aid != agent_id
            ]

        await self._emit_queue_update()

    async def _emit_queue_update(self) -> None:
        """Emit the current hand-raise queue to the frontend."""
        queue = [
            {"agentId": aid, "position": i + 1}
            for i, (aid, _, _) in enumerate(self._hand_raise_queue)
        ]
        await self.emit(
            "hand_raise_queue", {"queue": queue}
        )

    def _select_next_from_queue(
        self,
    ) -> Optional[tuple[str, CandidateQuestion, float]]:
        """Pick the best agent from the hand-raise queue. Removes from queue."""
        if not self._hand_raise_queue:
            return None

        if len(self._hand_raise_queue) == 1:
            return self._hand_raise_queue.pop(0)

        # Fairness + priority scoring
        scored = []
        for item in self._hand_raise_queue:
            aid, candidate, raised_at = item
            agent_ctx = self.session_context.get_agent_context(aid)
            qcount = agent_ctx.total_questions
            priority = (
                candidate.relevance_score if candidate else 0.5
            )
            # Lower question count = higher priority
            # Higher relevance = higher priority
            # Earlier raise = slight priority
            score = (
                priority
                - (qcount * 0.3)
                + (1.0 / (time.time() - raised_at + 1))
            )
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        _, best = scored[0]
        self._hand_raise_queue.remove(best)

        # Log queue decision (fire-and-forget)
        asyncio.create_task(self.session_logger.log_queue_decision(
            queue_snapshot=[
                {"agent_id": aid, "relevance": c.relevance_score if c else 0}
                for aid, c, _ in self._hand_raise_queue
            ],
            selected_agent=best[0],
            scores=[
                {"agent_id": item[0], "score": round(s, 3)}
                for s, item in scored
            ],
        ))

        return best

    # --- Moderator loop ---

    async def _moderator_loop(self) -> None:
        """Periodically check hand-raise queue and call on agents."""
        try:
            # Wait for initial setup
            await asyncio.sleep(3)

            while self._running:
                await asyncio.sleep(2)

                if not self._running:
                    break

                # Don't call on anyone during an exchange
                if self.session_context.state == SessionState.EXCHANGE:
                    continue

                # Breathing room after an exchange resolves
                if self._last_exchange_resolved_at > 0:
                    since_resolved = time.time() - self._last_exchange_resolved_at
                    if since_resolved < self._post_exchange_pause_secs:
                        continue

                async with self._hand_raise_lock:
                    item = self._select_next_from_queue()

                if item:
                    agent_id, candidate, raised_at = item
                    await self._call_on_agent(agent_id, candidate)

        except asyncio.CancelledError:
            pass

    async def _call_on_agent(
        self, agent_id: str, candidate: CandidateQuestion
    ) -> None:
        """Moderator calls on an agent. Agent speaks immediately."""
        # Verify the runner still has a buffered question (may have been
        # invalidated by a slide change between hand-raise and being called on)
        runner = self.runners.get(agent_id)
        if runner and not runner.buffered_question:
            logger.info(
                f"Agent {agent_id} was called on but has no buffered question "
                f"(likely invalidated by slide change). Skipping."
            )
            return

        self.session_context.state = SessionState.QA_TRIGGER

        # Log moderator calling on agent
        await self.session_logger.log_moderator("call_on_agent", {
            "agent_id": agent_id,
            "question_text": candidate.text if candidate else "",
            "slide_index": candidate.slide_index if candidate else self.current_slide,
        })

        # Emit moderator transition TTS
        await self._emit_moderator_transition(agent_id)

        # Signal the agent to deliver its question
        await self.event_bus.publish(
            Event(
                type=EventType.AGENT_CALLED_ON,
                data={"agent_id": agent_id},
                source="moderator",
            )
        )

        # Small yield to let agent process the event
        await asyncio.sleep(0.1)

        # Create exchange
        exchange = Exchange(
            agent_id=agent_id,
            question_text=candidate.text if candidate else "",
            target_claim=candidate.target_claim if candidate else "",
            slide_index=(
                candidate.slide_index if candidate else self.current_slide
            ),
        )
        exchange.turns.append(
            ExchangeTurn(speaker="agent", text=exchange.question_text)
        )
        self.session_context.active_exchange = exchange
        self.session_context.state = SessionState.EXCHANGE

        # Publish exchange started
        await self.event_bus.publish(
            Event(
                type=EventType.EXCHANGE_STARTED,
                data={
                    "agent_id": agent_id,
                    "exchange_id": exchange.id,
                },
                source="moderator",
            )
        )

        max_turns = self._turn_limits.get(self.config["intensity"], 3)
        await self.emit(
            "session_state",
            {
                "state": "exchange",
                "agentId": agent_id,
                "exchangeId": exchange.id,
                "maxTurns": max_turns,
            },
        )

        # Start exchange timeout
        await self._start_exchange_timer()

        # Emit queue update (agent was removed from queue)
        await self._emit_queue_update()

    # --- Exchange handling ---

    async def _handle_exchange_response(self, segment: dict) -> None:
        """Handle a presenter's response during an active exchange.

        Accumulates transcript segments and waits for the presenter to finish
        speaking (3s pause + minimum 8 words) before triggering agent
        assessment. This prevents the agent from jumping in mid-sentence.
        """
        exchange = self.session_context.active_exchange
        if not exchange:
            return

        text = segment.get("text", "").strip()
        if not text:
            return

        # Reset exchange timeout since presenter is actively speaking
        self._cancel_exchange_timer()
        await self._start_exchange_timer()

        # Accumulate this segment
        self._exchange_response_buffer.append(text)
        total_text = " ".join(self._exchange_response_buffer)
        word_count = len(total_text.split())

        logger.debug(
            f"Exchange response buffer: {word_count} words "
            f"({len(self._exchange_response_buffer)} segments)"
        )

        # Cancel previous debounce if presenter is still speaking
        if (
            self._exchange_response_debounce
            and not self._exchange_response_debounce.done()
        ):
            self._exchange_response_debounce.cancel()

        # Only start debounce if we have enough words
        if word_count >= self._exchange_min_words:
            self._exchange_response_debounce = asyncio.create_task(
                self._debounced_exchange_assessment()
            )
        # If under threshold, just keep accumulating — the exchange timeout
        # will eventually resolve if presenter stays silent

    async def _debounced_exchange_assessment(self) -> None:
        """Wait for presenter to stop speaking, then assess the full response."""
        try:
            await asyncio.sleep(self._exchange_response_pause_secs)
        except asyncio.CancelledError:
            return  # Presenter spoke again, debounce reset

        exchange = self.session_context.active_exchange
        if not exchange:
            self._exchange_response_buffer.clear()
            return

        # Combine all buffered segments into one presenter turn
        full_response = " ".join(self._exchange_response_buffer)
        self._exchange_response_buffer.clear()

        if not full_response.strip():
            return

        # Cancel timeout — we're processing now
        self._cancel_exchange_timer()

        # Record presenter turn
        exchange.turns.append(
            ExchangeTurn(speaker="presenter", text=full_response)
        )

        # Log presenter response in exchange
        await self.session_logger.log_agent_exchange(
            exchange.agent_id,
            "presenter_response",
            {
                "text": full_response,
                "exchange_id": exchange.id,
                "turn": exchange.turn_count,
            },
        )

        agent_id = exchange.agent_id
        max_turns = self._turn_limits.get(self.config["intensity"], 3)

        # Check turn limit
        if exchange.presenter_turn_count >= max_turns:
            await self._resolve_exchange(exchange, ExchangeOutcome.TURN_LIMIT)
            return

        # Emit thinking indicator
        await self.emit("agent_thinking", {"agentId": agent_id})

        # Play filler IMMEDIATELY while LLM assesses
        filler_url = self.filler_service.get_random_filler(agent_id)
        if filler_url:
            await self.emit(
                "agent_filler",
                {"agentId": agent_id, "audioUrl": filler_url},
            )

        # Ask the agent runner to assess (runs while filler plays ~1-2s)
        runner = self.runners.get(agent_id)
        if not runner:
            await self._resolve_exchange(exchange, ExchangeOutcome.SATISFIED)
            return

        try:
            result = await runner.handle_exchange_follow_up(exchange)
        except Exception as e:
            logger.warning(f"Follow-up assessment failed: {e}")
            await self._resolve_exchange(exchange, ExchangeOutcome.SATISFIED)
            return

        if result is None:
            # Agent satisfied
            exchange.evaluation_reasoning = "Agent satisfied with response"
            await self._resolve_exchange(exchange, ExchangeOutcome.SATISFIED)
        else:
            # Agent has follow-up
            exchange.evaluation_reasoning = result.get("reasoning", "")
            await self._emit_agent_follow_up(
                agent_id, result["text"], result.get("audio_url"), exchange
            )

    async def _emit_agent_follow_up(
        self,
        agent_id: str,
        text: str,
        audio_url: Optional[str],
        exchange: Exchange,
    ) -> None:
        """Emit an agent follow-up question during an exchange."""
        exchange.turns.append(ExchangeTurn(speaker="agent", text=text))

        await self._store_transcript_entry(
            agent_id, text, entry_type="follow_up"
        )

        max_turns = self._turn_limits.get(self.config["intensity"], 3)
        await self.emit(
            "agent_follow_up",
            {
                "agentId": agent_id,
                "agentName": AGENT_NAMES.get(agent_id, agent_id),
                "agentRole": AGENT_ROLES.get(agent_id, ""),
                "text": text,
                "audioUrl": audio_url,
                "turnNumber": exchange.agent_turn_count,
                "maxTurns": max_turns,
                "exchangeId": exchange.id,
            },
        )

        # Restart exchange timeout
        await self._start_exchange_timer()

    async def _resolve_exchange(
        self, exchange: Exchange, outcome: ExchangeOutcome
    ) -> None:
        """Resolve the current exchange and transition back to PRESENTING."""
        self._cancel_exchange_timer()
        self._exchange_response_buffer.clear()
        if (
            self._exchange_response_debounce
            and not self._exchange_response_debounce.done()
        ):
            self._exchange_response_debounce.cancel()
            self._exchange_response_debounce = None

        exchange.outcome = outcome
        exchange.resolved_at = time.time()

        # Log exchange resolution
        await self.session_logger.log_agent_exchange(
            exchange.agent_id, "resolved",
            {
                "exchange_id": exchange.id,
                "outcome": outcome.value,
                "turn_count": exchange.turn_count,
                "reasoning": exchange.evaluation_reasoning,
                "turns": [{"speaker": t.speaker, "text": t.text} for t in exchange.turns],
            },
        )

        agent_id = exchange.agent_id
        agent_ctx = self.session_context.get_agent_context(agent_id)
        agent_ctx.exchanges.append(exchange)
        if exchange.target_claim:
            agent_ctx.challenged_claims.append(exchange.target_claim)

        self.session_context.completed_exchanges.append(exchange)
        self.session_context.active_exchange = None
        self.session_context.state = SessionState.RESOLVING

        # Update presenter profile
        self._update_presenter_profile(agent_id, exchange)

        await self.emit(
            "exchange_resolved",
            {
                "exchangeId": exchange.id,
                "agentId": agent_id,
                "outcome": outcome.value,
            },
        )

        # Moderator bridge-back
        await self._emit_moderator_bridge_back(exchange)

        # Back to presenting (with breathing room)
        self._last_exchange_resolved_at = time.time()
        self.session_context.state = SessionState.PRESENTING
        await self.emit("session_state", {"state": "presenting"})

        # Broadcast exchange resolved so agents resume
        await self.event_bus.publish(
            Event(
                type=EventType.EXCHANGE_RESOLVED,
                data={
                    "agent_id": agent_id,
                    "outcome": outcome.value,
                    "exchange_id": exchange.id,
                },
                source="moderator",
            )
        )

    # --- Exchange timeout ---

    async def _start_exchange_timer(self) -> None:
        self._cancel_exchange_timer()
        self._exchange_timeout_task = asyncio.create_task(
            self._exchange_timeout_handler()
        )

    async def _exchange_timeout_handler(self) -> None:
        try:
            await asyncio.sleep(self._exchange_timeout_secs)
            exchange = self.session_context.active_exchange
            if exchange and not exchange.is_resolved:
                logger.info(
                    f"Exchange {exchange.id} timed out after "
                    f"{self._exchange_timeout_secs}s"
                )
                await self._resolve_exchange(
                    exchange, ExchangeOutcome.TIMEOUT
                )
        except asyncio.CancelledError:
            pass

    def _cancel_exchange_timer(self) -> None:
        if (
            self._exchange_timeout_task
            and not self._exchange_timeout_task.done()
        ):
            self._exchange_timeout_task.cancel()
            self._exchange_timeout_task = None

    # --- Moderator speech ---

    async def _emit_moderator(
        self, text: str, is_static: bool = False
    ) -> None:
        """Emit a moderator message with TTS audio."""
        audio_url = None

        if is_static:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            resources_dir = os.path.join(base_dir, "resources")
            common_assets_dir = os.path.join(resources_dir, "common_assets")
            moderator_pattern = os.path.join(
                common_assets_dir, "moderator*.wav"
            )
            moderator_files = glob.glob(moderator_pattern)
            if moderator_files:
                moderator_files.sort()
                selected_file = moderator_files[0]
                rel_path = os.path.relpath(selected_file, resources_dir)
                rel_path = rel_path.replace(os.sep, "/")
                audio_url = f"/api/resources/{rel_path}"
        else:
            try:
                audio_url = await self.tts.synthesize(
                    "moderator", text, session_id=self.session_id
                )
            except Exception as e:
                logger.warning(f"TTS failed for moderator: {e}. Text-only.")

        await self._store_transcript_entry(
            "moderator", text, entry_type="moderator"
        )

        await self.emit(
            "moderator_message",
            {
                "text": text,
                "audioUrl": audio_url,
                "agentName": AGENT_NAMES["moderator"],
                "agentRole": AGENT_ROLES["moderator"],
            },
        )

    async def _emit_moderator_transition(self, agent_id: str) -> None:
        """Emit a moderator transition phrase before calling on an agent."""
        from app.services.template_loader import get_template

        phrase_library = get_template("moderator", "phrase-library") or ""
        agent_name = AGENT_NAMES.get(agent_id, agent_id)

        transitions = self._parse_transition_phrases(phrase_library, agent_id)
        if transitions:
            phrase = random.choice(transitions)
        else:
            phrase = (
                f"Thank you for that. {agent_name}, go ahead with your question."
            )

        await self._emit_moderator(phrase)

    def _parse_transition_phrases(
        self, phrase_library: str, agent_id: str
    ) -> list[str]:
        """Extract transition phrases for a specific agent from phrase library."""
        agent_name_map = {
            "skeptic": "Marcus",
            "analyst": "Priya",
            "contrarian": "James",
            "technologist": "Rachel",
            "coo": "Sandra",
            "ceo": "Michael",
            "cio": "Robert",
            "chro": "Lisa",
            "cco": "Thomas",
        }
        target_name = agent_name_map.get(agent_id)
        if not target_name or not phrase_library:
            return []

        phrases = []
        in_section = False
        for line in phrase_library.split("\n"):
            if f"To {target_name}" in line:
                in_section = True
                continue
            elif in_section and line.strip().startswith("###"):
                break
            elif in_section and line.strip().startswith("- "):
                phrase = line.strip().lstrip("- ").strip('"').strip()
                if phrase:
                    phrases.append(phrase)
        return phrases

    async def _emit_moderator_bridge_back(self, exchange: Exchange) -> None:
        """Emit a contextual moderator bridge-back after an exchange."""
        outcome = exchange.outcome

        if outcome == ExchangeOutcome.SATISFIED:
            bridge = (
                "Good. I think that concern has been addressed. "
                "Let's continue."
            )
        elif outcome in (
            ExchangeOutcome.MODERATOR_INTERVENED,
            ExchangeOutcome.TURN_LIMIT,
        ):
            bridge = (
                "We've surfaced an important issue here. "
                "We'll capture this in the debrief. Let's keep moving."
            )
        elif outcome == ExchangeOutcome.TIMEOUT:
            bridge = (
                "It seems we've moved on from that topic. "
                "Let's note it for the debrief and continue."
            )
        else:
            bridge = "Let's continue with the presentation."

        await self._emit_moderator(bridge)

    # --- Presenter profile ---

    def _update_presenter_profile(
        self, agent_id: str, exchange: Exchange
    ) -> None:
        """Update presenter profile based on exchange outcome."""
        agent_ctx = self.session_context.get_agent_context(agent_id)
        profile = agent_ctx.presenter_profile

        # Log profile before update
        asyncio.create_task(self.session_logger.log_presenter_profile({
            "agent_id": agent_id,
            "exchange_outcome": exchange.outcome.value if exchange.outcome else None,
            "data_readiness": profile.data_readiness,
            "response_patterns": profile.response_patterns[-3:],
            "recommended_strategy": profile.recommended_strategy,
        }))

        if exchange.outcome == ExchangeOutcome.SATISFIED:
            if exchange.presenter_turn_count <= 1:
                profile.response_patterns.append(
                    "Gave strong, direct answer"
                )
                profile.data_readiness = "strong"
            else:
                profile.response_patterns.append(
                    "Needed follow-up but eventually provided good answer"
                )
                profile.data_readiness = "moderate"
        elif exchange.outcome in (
            ExchangeOutcome.MODERATOR_INTERVENED,
            ExchangeOutcome.TURN_LIMIT,
        ):
            profile.response_patterns.append(
                "Could not satisfactorily address the question"
            )
            profile.data_readiness = "weak"
            profile.behavioral_notes.append(
                f"Struggled with: {exchange.question_text[:80]}"
            )
        elif exchange.outcome == ExchangeOutcome.ESCALATE:
            profile.response_patterns.append(
                "Response triggered escalation"
            )
            profile.recommended_strategy = "push_harder"
        elif exchange.outcome == ExchangeOutcome.TIMEOUT:
            profile.response_patterns.append(
                "Did not respond to the question"
            )
            profile.data_readiness = "weak"
            profile.behavioral_notes.append(
                f"No response to: {exchange.question_text[:80]}"
            )

    # --- Time warnings ---

    def _check_time_warnings(self) -> Optional[str]:
        """Check if we need to emit time warnings."""
        session_duration = self.config.get("duration_secs", 600)
        elapsed = self._elapsed_seconds()
        pct = elapsed / max(session_duration, 1)

        if pct >= 0.9 and not self._time_warning_90_sent:
            self._time_warning_90_sent = True
            remaining_mins = max(1, int((session_duration - elapsed) / 60))
            return (
                f"We have about {remaining_mins} "
                f"minute{'s' if remaining_mins > 1 else ''} left. "
                f"Let's prioritize."
            )
        elif pct >= 0.8 and not self._time_warning_80_sent:
            self._time_warning_80_sent = True
            remaining_mins = max(1, int((session_duration - elapsed) / 60))
            return (
                f"About {remaining_mins} minutes remaining. "
                f"Make sure to cover your key points."
            )
        return None

    # --- Transcript storage ---

    async def _store_transcript_entry(
        self,
        agent_id: str,
        text: str,
        entry_type: str = "question",
    ) -> None:
        """Store a transcript entry in the database."""
        try:
            from app.models.base import async_session_factory
            from app.models.transcript import TranscriptEntry

            async with async_session_factory() as db:
                # Use elapsed milliseconds as entry_index to avoid collisions
                # across concurrent writers (coordinator + multiple runners)
                entry_index = int(self._elapsed_seconds() * 1000)
                if agent_id == "presenter":
                    speaker = "presenter"
                    speaker_name = "Presenter"
                    agent_role = "Presenter"
                elif agent_id == "moderator":
                    speaker = "moderator"
                    speaker_name = AGENT_NAMES.get(agent_id, agent_id)
                    agent_role = AGENT_ROLES.get(agent_id)
                else:
                    speaker = f"agent_{agent_id}"
                    speaker_name = AGENT_NAMES.get(agent_id, agent_id)
                    agent_role = AGENT_ROLES.get(agent_id)

                entry = TranscriptEntry(
                    session_id=self.session_id,
                    entry_index=entry_index,
                    speaker=speaker,
                    speaker_name=speaker_name,
                    agent_role=agent_role,
                    text=text,
                    start_time=self._elapsed_seconds(),
                    end_time=self._elapsed_seconds(),
                    slide_index=self.current_slide,
                    entry_type=entry_type,
                )
                db.add(entry)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to store transcript entry: {e}")


# Backward-compatible alias so imports like `from app.services.agent_engine import AgentEngine` still work
AgentEngine = SessionCoordinator
