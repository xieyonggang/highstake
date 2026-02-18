"""Autonomous agent background task.

Each AgentRunner observes session events, independently decides when to ask
questions, generates question text + TTS audio, and raises its hand when
ready to speak. The SessionCoordinator sees raised hands and calls on agents.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Awaitable

from app.services.agent_prompts import (
    AGENT_NAMES,
    AGENT_ROLES,
    AGENT_TITLES,
    build_agent_prompt,
    build_evaluation_prompt,
)

# Per-agent fallback questions when LLM fails
FALLBACK_QUESTIONS = {
    "skeptic": [
        "What evidence supports this claim?",
        "How does this compare to industry benchmarks?",
        "What are the key risks you've identified?",
    ],
    "analyst": [
        "Could you walk us through the underlying data?",
        "What assumptions drive these projections?",
        "How sensitive are these numbers to market changes?",
    ],
    "contrarian": [
        "Have you considered an alternative approach?",
        "What would happen if the opposite were true?",
        "Who would disagree with this and why?",
    ],
}
from app.services.context_manager import ContextManager
from app.services.event_bus import Event, EventBus, EventType
from app.services.llm_client import LLMClient
from app.services.session_context import (
    AgentSessionContext,
    CandidateQuestion,
    Exchange,
    ExchangeOutcome,
    ExchangeTurn,
)
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)


class AgentRunnerState(str, Enum):
    IDLE = "idle"
    EVALUATING = "evaluating"
    GENERATING = "generating"
    READY = "ready"
    SPEAKING = "speaking"
    IN_EXCHANGE = "in_exchange"
    COOLDOWN = "cooldown"


@dataclass
class AgentContext:
    """Per-agent accumulated observation context."""

    agent_id: str
    current_slide: int = 0
    transcript_segments: list[dict] = field(default_factory=list)
    other_agent_questions: list[dict] = field(default_factory=list)
    exchange_active: bool = False
    exchange_agent: Optional[str] = None
    last_eval_transcript_count: int = 0

    def add_transcript(self, segment: dict):
        self.transcript_segments.append(segment)

    def set_slide(self, index: int):
        self.current_slide = index

    def set_exchange_active(self, active: bool, agent_id: Optional[str]):
        self.exchange_active = active
        self.exchange_agent = agent_id

    def add_other_agent_question(self, data: dict):
        if data.get("agent_id") != self.agent_id:
            self.other_agent_questions.append(data)

    def has_sufficient_context(self) -> bool:
        # Need presenter to be past title/agenda slides (first 2-3 slides)
        # AND have meaningful transcript before evaluating
        total_words = sum(
            len(s.get("text", "").split()) for s in self.transcript_segments
        )
        # Require at least slide 3 (past title + agenda) and 50+ words of content
        if self.current_slide >= 3 and total_words >= 50:
            return True
        # Or if we have substantial transcript even on early slides (presenter speaking a lot)
        if total_words >= 150:
            return True
        return False

    def get_transcript_text(self, last_n: int = 20) -> str:
        segments = self.transcript_segments[-last_n:]
        return "\n".join(s.get("text", "") for s in segments if s.get("text"))


# Staggered base intervals per agent index to avoid LLM bursts
_EVAL_INTERVALS = [8.0, 10.0, 12.0, 9.0, 11.0, 7.0, 13.0, 8.5, 10.5, 11.5]


class AgentRunner:
    """Autonomous agent that runs as an independent asyncio.Task."""

    def __init__(
        self,
        agent_id: str,
        agent_index: int,
        session_id: str,
        config: dict,
        deck_manifest: dict,
        claims_by_slide: dict,
        event_bus: EventBus,
        llm_client: LLMClient,
        tts_service: TTSService,
        emit_callback: Callable[[str, dict], Awaitable[None]],
        session_context: AgentSessionContext,
        llm_semaphore: Optional[asyncio.Semaphore] = None,
        session_logger=None,
    ):
        self.agent_id = agent_id
        self.session_id = session_id
        self.config = config
        self.deck_manifest = deck_manifest
        self.claims_by_slide = claims_by_slide
        self.event_bus = event_bus
        self.llm = llm_client
        self.tts = tts_service
        self.emit = emit_callback
        self._llm_semaphore = llm_semaphore
        self._session_logger = session_logger

        # Per-agent session context (shared with coordinator for exchange tracking)
        self.agent_session_ctx = session_context

        # Internal state
        self.state = AgentRunnerState.IDLE
        self.observation = AgentContext(agent_id=agent_id)
        self.context_manager = ContextManager()
        self.buffered_question: Optional[CandidateQuestion] = None
        self.previous_questions: list[dict] = []
        self.question_count: int = 0

        # Task management
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._new_input_event = asyncio.Event()
        self._called_on_event = asyncio.Event()

        # Timing
        self._session_start: float = time.time()
        self._last_question_time: float = 0
        self._evaluation_interval: float = _EVAL_INTERVALS[
            agent_index % len(_EVAL_INTERVALS)
        ]
        self._cooldown_secs: float = 15.0
        self._transcript_entry_count: int = 0

    async def start(self):
        """Start the autonomous agent loop."""
        self.event_bus.subscribe_all(self._on_event)
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"AgentRunner started: {self.agent_id} "
            f"(eval_interval={self._evaluation_interval}s)"
        )

    async def stop(self):
        """Stop the agent gracefully."""
        self._stop_event.set()
        self._new_input_event.set()
        self._called_on_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"AgentRunner stopped: {self.agent_id}")

    def _elapsed_seconds(self) -> float:
        return time.time() - self._session_start

    # --- Event handling ---

    async def _on_event(self, event: Event):
        """Update internal context based on session events."""
        if event.type == EventType.TRANSCRIPT_UPDATE:
            self.observation.add_transcript(event.data)
            self.context_manager.add_segment(event.data)
            if self.state == AgentRunnerState.IDLE:
                self._new_input_event.set()

        elif event.type == EventType.SLIDE_CHANGED:
            new_slide = event.data.get("slide_index", 0)
            self.observation.set_slide(new_slide)
            self.context_manager.current_slide_index = new_slide
            # Invalidate stale buffered question
            if (
                self.buffered_question
                and self.buffered_question.slide_index != new_slide
            ):
                self.buffered_question = None
                if self.state == AgentRunnerState.READY:
                    self.state = AgentRunnerState.IDLE
                    await self.event_bus.publish(
                        Event(
                            type=EventType.HAND_LOWERED,
                            data={
                                "agent_id": self.agent_id,
                                "reason": "slide_changed",
                            },
                            source=self.agent_id,
                        )
                    )
                    await self.emit(
                        "agent_hand_lowered", {"agentId": self.agent_id}
                    )
            if self.state == AgentRunnerState.IDLE:
                self._new_input_event.set()

        elif event.type == EventType.EXCHANGE_STARTED:
            self.observation.set_exchange_active(True, event.data.get("agent_id"))

        elif event.type == EventType.EXCHANGE_RESOLVED:
            self.observation.set_exchange_active(False, None)
            if event.data.get("agent_id") == self.agent_id:
                self.state = AgentRunnerState.COOLDOWN
                asyncio.create_task(self._cooldown_then_idle())
            elif self.state == AgentRunnerState.IDLE:
                # After another agent's exchange resolves, re-evaluate
                self._new_input_event.set()

        elif event.type == EventType.AGENT_SPOKE:
            self.observation.add_other_agent_question(event.data)

        elif event.type == EventType.AGENT_CALLED_ON:
            if event.data.get("agent_id") == self.agent_id:
                self._called_on_event.set()

        elif event.type == EventType.CLAIMS_READY:
            self.claims_by_slide = event.data.get("claims_by_slide", {})

        elif event.type == EventType.SESSION_ENDING:
            await self.stop()

    # --- Main autonomous loop ---

    async def _run_loop(self):
        """Observe → evaluate → generate → raise hand → wait → speak."""
        try:
            # Wait 3-5 min so presenter gets past title/agenda slides
            initial_delay = 180.0 + (self._evaluation_interval * 2.0)
            logger.info(
                f"Agent {self.agent_id}: waiting {initial_delay:.0f}s "
                f"before first evaluation"
            )
            await self._log_state("INIT", "WAITING", f"initial_delay={initial_delay:.0f}s")
            await asyncio.sleep(initial_delay)
            await self._log_state("WAITING", "IDLE", "initial_delay_complete")

            while not self._stop_event.is_set():
                if self.state == AgentRunnerState.IDLE:
                    # Wait for new input or periodic re-evaluation
                    try:
                        await asyncio.wait_for(
                            self._new_input_event.wait(),
                            timeout=self._evaluation_interval,
                        )
                    except asyncio.TimeoutError:
                        pass
                    self._new_input_event.clear()

                    if self._stop_event.is_set():
                        break

                    # Skip if another agent is in exchange
                    if self.observation.exchange_active:
                        continue

                    # Skip if not enough context
                    if not self.observation.has_sufficient_context():
                        continue

                    # Evaluate
                    self.state = AgentRunnerState.EVALUATING
                    should_ask = self._evaluate_should_ask()

                    if should_ask:
                        await self._log_state("EVALUATING", "GENERATING", "should_ask=True")
                        self.state = AgentRunnerState.GENERATING
                        await self.emit(
                            "agent_thinking", {"agentId": self.agent_id}
                        )

                        candidate = await self._generate_question()
                        if candidate and not self._stop_event.is_set():
                            self.buffered_question = candidate
                            self.state = AgentRunnerState.READY

                            # Raise hand — question + audio are ready
                            await self.event_bus.publish(
                                Event(
                                    type=EventType.HAND_RAISED,
                                    data={
                                        "agent_id": self.agent_id,
                                        "question": candidate,
                                        "priority": candidate.relevance_score,
                                    },
                                    source=self.agent_id,
                                )
                            )
                            await self.emit(
                                "agent_hand_raise",
                                {"agentId": self.agent_id},
                            )

                            logger.info(
                                f"Agent {self.agent_id} raised hand "
                                f"(slide={candidate.slide_index})"
                            )

                            # Wait until moderator calls on us
                            self._called_on_event.clear()
                            try:
                                await asyncio.wait_for(
                                    self._called_on_event.wait(),
                                    timeout=60.0,
                                )
                            except asyncio.TimeoutError:
                                # Timed out waiting — lower hand and retry
                                logger.info(
                                    f"Agent {self.agent_id} hand-raise timed out"
                                )
                                self.buffered_question = None
                                self.state = AgentRunnerState.IDLE
                                await self.event_bus.publish(
                                    Event(
                                        type=EventType.HAND_LOWERED,
                                        data={
                                            "agent_id": self.agent_id,
                                            "reason": "timeout",
                                        },
                                        source=self.agent_id,
                                    )
                                )
                                continue

                            if self._stop_event.is_set():
                                break

                            # Deliver the question
                            await self._deliver_question()
                        else:
                            self.state = AgentRunnerState.IDLE
                    else:
                        self.state = AgentRunnerState.IDLE

                elif self.state in (
                    AgentRunnerState.SPEAKING,
                    AgentRunnerState.IN_EXCHANGE,
                ):
                    await asyncio.sleep(1)

                elif self.state == AgentRunnerState.COOLDOWN:
                    await asyncio.sleep(1)

                elif self.state == AgentRunnerState.READY:
                    # Shouldn't normally reach here — wait is in IDLE→READY flow
                    await asyncio.sleep(0.5)

                else:
                    await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"AgentRunner {self.agent_id} loop error: {e}", exc_info=True)

    async def _cooldown_then_idle(self):
        """Post-exchange cooldown before resuming evaluation."""
        await asyncio.sleep(self._cooldown_secs)
        if self.state == AgentRunnerState.COOLDOWN:
            self.state = AgentRunnerState.IDLE
            self._new_input_event.set()

    # --- Question evaluation ---

    def _evaluate_should_ask(self) -> bool:
        """Heuristic evaluation: should this agent ask a question now?"""
        elapsed = self._elapsed_seconds()

        # Cooldown check
        if self._last_question_time > 0:
            if elapsed - self._last_question_time < self._cooldown_secs:
                self._log_decision_sync(False, "cooldown")
                return False

        # Need some transcript to work with
        transcript_growth = (
            len(self.observation.transcript_segments)
            - self.observation.last_eval_transcript_count
        )
        self.observation.last_eval_transcript_count = len(
            self.observation.transcript_segments
        )

        if not self.observation.transcript_segments:
            return False

        # Check for unchallenged claims on current slide
        current_claims = self.claims_by_slide.get(
            self.observation.current_slide, []
        )
        challenged = set(self.agent_session_ctx.challenged_claims)
        unchallenged = [
            c
            for c in current_claims
            if c.get("text") and c["text"] not in challenged
        ]

        # Must have either new transcript or unchallenged claims
        if transcript_growth < 2 and not unchallenged:
            self._log_decision_sync(False, "insufficient_growth")
            return False

        # Time-based urgency (ask more near end of session)
        session_duration = self.config.get("duration_secs", 600)
        time_pressure = elapsed / max(session_duration, 1)

        heuristics = {
            "transcript_growth": transcript_growth,
            "unchallenged_claims": len(unchallenged),
            "time_pressure": round(time_pressure, 3),
            "slide": self.observation.current_slide,
            "total_segments": len(self.observation.transcript_segments),
            "question_count": self.question_count,
        }

        # Higher chance of asking with unchallenged claims or time pressure
        result = False
        reason = "no_trigger"
        if unchallenged:
            result = True
            reason = "unchallenged_claims"
        elif transcript_growth >= 3 and time_pressure > 0.3:
            result = True
            reason = "transcript_growth+time_pressure"
        elif transcript_growth >= 5:
            result = True
            reason = "high_transcript_growth"

        # Log decision
        heuristics["reason"] = reason
        self._log_decision_sync(result, reason, heuristics)

        return result

    def _log_decision_sync(self, should_ask: bool, reason: str, heuristics: dict = None):
        """Fire-and-forget log of evaluation decision."""
        if self._session_logger:
            asyncio.create_task(self._session_logger.log_agent_decision(
                self.agent_id, should_ask,
                heuristics or {"reason": reason},
            ))

    # --- Question generation ---

    async def _generate_question(self) -> Optional[CandidateQuestion]:
        """Generate question text + TTS audio. Returns CandidateQuestion."""
        target_claim = self._get_target_claim()

        context = self.context_manager.get_context_for_agent(
            self.agent_id,
            self.observation.current_slide,
            self.deck_manifest,
            self._elapsed_seconds(),
        )

        # Log context snapshot
        if self._session_logger:
            await self._session_logger.log_agent_context(self.agent_id, context)

        exchange_history = self._format_exchange_history()
        cross_agent = self._format_cross_agent_summary()
        if cross_agent:
            exchange_history = (
                (exchange_history + "\n\n" + cross_agent)
                if exchange_history
                else cross_agent
            )

        presenter_profile = self.agent_session_ctx.presenter_profile.to_text()

        prompt = build_agent_prompt(
            agent_id=self.agent_id,
            intensity=self.config["intensity"],
            focus_areas=self.config.get("focus_areas", []),
            slide_index=self.observation.current_slide,
            total_slides=self.deck_manifest.get("totalSlides", 6),
            slide_title=context.get("current_slide_title", ""),
            slide_content=context.get("current_slide_text", ""),
            slide_notes=context.get("current_slide_notes", ""),
            transcript=context.get("transcript_text", ""),
            previous_questions=[q["text"] for q in self.previous_questions],
            elapsed_time=self._elapsed_seconds(),
            exchange_history=exchange_history,
            presenter_profile=presenter_profile,
            target_claim=target_claim,
        )

        question_text = None
        try:
            if self._llm_semaphore:
                async with self._llm_semaphore:
                    question_text = await self.llm.generate_question(
                        system_prompt=prompt,
                        context_messages=[
                            {"role": "user", "content": "Ask exactly ONE focused question now. Do not ask multiple questions or combine questions. Keep it to a single, direct question."}
                        ],
                    )
            else:
                question_text = await self.llm.generate_question(
                    system_prompt=prompt,
                    context_messages=[
                        {"role": "user", "content": "Ask exactly ONE focused question now. Do not ask multiple questions or combine questions. Keep it to a single, direct question."}
                    ],
                )
        except Exception as e:
            logger.warning(
                f"LLM failed for {self.agent_id}: {e}. Using fallback."
            )
            question_text = self._get_fallback_question()

        audio_url = None
        try:
            audio_url = await self.tts.synthesize(
                self.agent_id, question_text, session_id=self.session_id
            )
        except Exception as e:
            logger.warning(f"TTS failed for {self.agent_id}: {e}. Text-only.")

        candidate = CandidateQuestion(
            agent_id=self.agent_id,
            text=question_text,
            target_claim=target_claim,
            slide_index=self.observation.current_slide,
            audio_url=audio_url,
            relevance_score=0.8,
        )

        # Log the full question generation: prompt, response, candidate
        if self._session_logger:
            await self._session_logger.log_agent_question(
                self.agent_id,
                system_prompt=prompt,
                llm_response=question_text,
                candidate={
                    "text": candidate.text,
                    "target_claim": candidate.target_claim,
                    "slide_index": candidate.slide_index,
                    "audio_url": candidate.audio_url,
                },
            )

        return candidate

    async def _deliver_question(self):
        """Called when moderator says 'go ahead'. Emit the buffered question."""
        if not self.buffered_question:
            return

        q = self.buffered_question
        await self._log_state("READY", "SPEAKING", f"delivering question: {q.text[:80]}")
        self.state = AgentRunnerState.SPEAKING
        self._last_question_time = time.time()
        self.question_count += 1

        self.previous_questions.append(
            {"agent_id": self.agent_id, "text": q.text}
        )

        # Store transcript entry
        await self._store_transcript_entry(q.text)

        # Emit to frontend — audio is already generated!
        await self.emit(
            "agent_question",
            {
                "agentId": self.agent_id,
                "agentName": AGENT_NAMES.get(self.agent_id, self.agent_id),
                "agentRole": AGENT_ROLES.get(self.agent_id, ""),
                "agentTitle": AGENT_TITLES.get(self.agent_id, ""),
                "text": q.text,
                "audioUrl": q.audio_url,
                "slideRef": q.slide_index,
            },
        )

        # Publish so other agents + coordinator know
        await self.event_bus.publish(
            Event(
                type=EventType.AGENT_SPOKE,
                data={
                    "agent_id": self.agent_id,
                    "text": q.text,
                    "slide_index": q.slide_index,
                },
                source=self.agent_id,
            )
        )

        self.state = AgentRunnerState.IN_EXCHANGE
        self.buffered_question = None

    # --- Exchange follow-up (called by coordinator) ---

    async def handle_exchange_follow_up(
        self, exchange: Exchange
    ) -> Optional[dict]:
        """Evaluate presenter response and generate follow-up if needed.

        Called by SessionCoordinator during this agent's exchange.
        Returns {"text": str, "audio_url": str|None} or None if satisfied.
        """
        # Build exchange history text
        history_lines = []
        for turn in exchange.turns:
            speaker_label = "Agent" if turn.speaker == "agent" else "Presenter"
            history_lines.append(f"{speaker_label}: {turn.text}")
        exchange_history_text = "\n".join(history_lines)

        eval_prompt = build_evaluation_prompt(
            agent_id=exchange.agent_id,
            question_text=exchange.question_text,
            exchange_history=exchange_history_text,
        )

        try:
            evaluation = await self.llm.evaluate_response(
                system_prompt=eval_prompt,
                exchange_text=exchange_history_text,
            )
        except Exception as e:
            logger.warning(
                f"Evaluation failed for {self.agent_id}: {e}"
            )
            return None  # Accept on failure

        verdict = evaluation.get("verdict", "SATISFIED").upper()
        reasoning = evaluation.get("reasoning", "")

        # Log the exchange evaluation
        if self._session_logger:
            await self._session_logger.log_agent_exchange(
                self.agent_id,
                "follow_up_eval",
                {
                    "eval_prompt": eval_prompt[:500],
                    "exchange_history": exchange_history_text,
                    "verdict": verdict,
                    "reasoning": reasoning,
                    "turn_count": len(exchange.turns),
                },
            )

        if verdict == "SATISFIED":
            return None

        if verdict in ("FOLLOW_UP", "ESCALATE"):
            follow_up = evaluation.get("follow_up", "")
            if not follow_up:
                return None

            audio_url = None
            try:
                audio_url = await self.tts.synthesize(
                    self.agent_id, follow_up, session_id=self.session_id
                )
            except Exception as e:
                logger.warning(
                    f"TTS failed for follow-up {self.agent_id}: {e}"
                )

            return {
                "text": follow_up,
                "audio_url": audio_url,
                "reasoning": reasoning,
            }

        return None

    # --- Context formatting helpers ---

    def _get_target_claim(self) -> str:
        """Get the most relevant unchallenged claim for the current slide."""
        claims = self.claims_by_slide.get(
            self.observation.current_slide, []
        )
        if not claims:
            return ""
        challenged = set(self.agent_session_ctx.challenged_claims)
        for claim in claims:
            claim_text = claim.get("text", "")
            if claim_text and claim_text not in challenged:
                return claim_text
        return ""

    def _format_exchange_history(self) -> str:
        """Format this agent's past exchanges for prompt context."""
        exchanges = self.agent_session_ctx.exchanges
        if not exchanges:
            return ""
        lines = []
        for i, exch in enumerate(exchanges[-3:], 1):
            lines.append(f"### Exchange {i}")
            lines.append(f"Question: {exch.question_text}")
            for turn in exch.turns:
                label = "You" if turn.speaker == "agent" else "Presenter"
                lines.append(f"  {label}: {turn.text}")
            lines.append(
                f"Outcome: {exch.outcome.value if exch.outcome else 'pending'}"
            )
            lines.append("")
        return "\n".join(lines)

    def _format_cross_agent_summary(self) -> str:
        """Format other agents' recent questions for cross-referencing."""
        if not self.observation.other_agent_questions:
            return ""
        lines = ["## Other Panelists' Recent Concerns"]
        for q in self.observation.other_agent_questions[-5:]:
            agent_name = AGENT_NAMES.get(q.get("agent_id", ""), "Unknown")
            text = q.get("text", "")[:120]
            lines.append(f'- {agent_name} asked: "{text}"')
        lines.append(
            "\nYou may reference or build upon their concerns if relevant. "
            "Use their names naturally."
        )
        return "\n".join(lines)

    def _get_fallback_question(self) -> str:
        """Return a fallback question if LLM fails."""
        questions = FALLBACK_QUESTIONS.get(self.agent_id, [])
        if questions:
            idx = self.question_count % len(questions)
            return questions[idx]
        return "Could you elaborate on that point?"

    async def _log_state(self, old: str, new: str, reason: str = "") -> None:
        """Fire-and-forget log of agent state transition."""
        if self._session_logger:
            await self._session_logger.log_agent_state(
                self.agent_id, old, new, reason
            )

    async def _store_transcript_entry(
        self, text: str, entry_type: str = "question"
    ) -> None:
        """Store a transcript entry in the database."""
        try:
            from app.models.base import async_session_factory
            from app.models.transcript import TranscriptEntry

            async with async_session_factory() as db:
                # Use elapsed milliseconds as entry_index to avoid collisions
                # across concurrent writers (coordinator + multiple runners)
                entry_index = int(self._elapsed_seconds() * 1000)
                entry = TranscriptEntry(
                    session_id=self.session_id,
                    entry_index=entry_index,
                    speaker=f"agent_{self.agent_id}",
                    speaker_name=AGENT_NAMES.get(self.agent_id, self.agent_id),
                    agent_role=AGENT_ROLES.get(self.agent_id),
                    text=text,
                    start_time=self._elapsed_seconds(),
                    end_time=self._elapsed_seconds(),
                    slide_index=self.observation.current_slide,
                    entry_type=entry_type,
                )
                db.add(entry)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to store transcript entry: {e}")
