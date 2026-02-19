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
from app.services.template_loader import get_agent_templates

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
    LOADING = "loading"
    LISTENING = "listening"
    EVALUATING = "evaluating"
    GENERATING = "generating"
    READY = "ready"
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

    def has_sufficient_context(self, min_words: int = 50) -> bool:
        """Check if there's enough presenter speech to evaluate.

        Context-based: requires meaningful transcript content regardless of
        slide number. The presenter may speak a lot on early slides or
        skip through slides quickly.
        """
        total_words = sum(
            len(s.get("text", "").split()) for s in self.transcript_segments
        )
        return total_words >= min_words

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
        self.state = AgentRunnerState.LISTENING
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
        self._claims_ready_event = asyncio.Event()
        if claims_by_slide:
            self._claims_ready_event.set()

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
            if self.state == AgentRunnerState.LISTENING:
                self._new_input_event.set()

        elif event.type == EventType.SLIDE_CHANGED:
            new_slide = event.data.get("slide_index", 0)
            self.observation.set_slide(new_slide)
            self.context_manager.current_slide_index = new_slide
            # Only invalidate buffered question if we're still generating
            # (not yet in queue). Once READY/in queue, the question about
            # the previous slide is still valid and should be addressed.
            if (
                self.buffered_question
                and self.buffered_question.slide_index != new_slide
                and self.state not in (
                    AgentRunnerState.READY,
                    AgentRunnerState.IN_EXCHANGE,
                )
            ):
                self.buffered_question = None
            if self.state == AgentRunnerState.LISTENING:
                self._new_input_event.set()

        elif event.type == EventType.EXCHANGE_STARTED:
            self.observation.set_exchange_active(True, event.data.get("agent_id"))

        elif event.type == EventType.EXCHANGE_RESOLVED:
            self.observation.set_exchange_active(False, None)
            if event.data.get("agent_id") == self.agent_id:
                self.state = AgentRunnerState.LISTENING
                self._new_input_event.set()
            elif self.state == AgentRunnerState.LISTENING:
                # After another agent's exchange resolves, re-evaluate
                self._new_input_event.set()

        elif event.type == EventType.AGENT_SPOKE:
            self.observation.add_other_agent_question(event.data)

        elif event.type == EventType.AGENT_CALLED_ON:
            if event.data.get("agent_id") == self.agent_id:
                # Coordinator now delivers the question directly.
                # Set our state to IN_EXCHANGE so we stop generating questions.
                self.state = AgentRunnerState.IN_EXCHANGE
                self.buffered_question = None
                self._last_question_time = time.time()
                self._called_on_event.set()

        elif event.type == EventType.CLAIMS_READY:
            self.claims_by_slide = event.data.get("claims_by_slide", {})
            self._claims_ready_event.set()

        elif event.type == EventType.SESSION_ENDING:
            self.state = AgentRunnerState.COOLDOWN
            await self.stop()

    # --- Main autonomous loop ---

    async def _run_loop(self):
        """Load context → warm up → evaluate → generate → raise hand → speak."""
        try:
            from app.config import settings as app_settings
            warmup_words = app_settings.agent_warmup_words

            # Stagger agents slightly so they don't all start at once.
            stagger_delay = 5.0 + (self._evaluation_interval * 0.5)
            await asyncio.sleep(stagger_delay)

            # --- Phase 1: LOADING ---
            # Wait for claims, pre-load templates, validate prompt building.
            self.state = AgentRunnerState.LOADING
            await self._log_state("INIT", "LOADING", "waiting for claims")
            logger.info(f"Agent {self.agent_id}: LOADING — waiting for claims...")

            _claims_timeout_secs = 30.0
            try:
                await asyncio.wait_for(
                    self._claims_ready_event.wait(),
                    timeout=_claims_timeout_secs,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"Agent {self.agent_id}: claims timeout after "
                    f"{_claims_timeout_secs}s, proceeding without claims"
                )

            if self._stop_event.is_set():
                return

            # Pre-load agent templates (warms the template cache)
            templates = get_agent_templates(self.agent_id)

            # Pre-build a baseline system prompt to validate templates work
            try:
                build_agent_prompt(
                    agent_id=self.agent_id,
                    intensity=self.config.get("intensity", "moderate"),
                    focus_areas=self.config.get("focus_areas", []),
                    slide_index=0,
                    total_slides=self.deck_manifest.get("totalSlides", 6),
                    slide_title="",
                    slide_content="",
                    slide_notes="",
                    transcript="",
                    previous_questions=[],
                )
            except Exception as e:
                logger.warning(
                    f"Agent {self.agent_id}: baseline prompt build failed: {e}"
                )

            claims_count = sum(
                len(v) for v in self.claims_by_slide.values()
            )
            logger.info(
                f"Agent {self.agent_id}: LOADED — "
                f"{claims_count} slide claims, "
                f"{len(templates)} templates ready"
            )

            await self.emit(
                "agent_loaded",
                {
                    "agentId": self.agent_id,
                    "claimsCount": claims_count,
                    "templatesLoaded": list(templates.keys()),
                },
            )

            await self._log_state("LOADING", "WARMING_UP", f"{claims_count} claims loaded")

            # --- Phase 2: WARMING UP ---
            # Wait for enough presenter speech before first evaluation.
            logger.info(
                f"Agent {self.agent_id}: warming up, waiting for "
                f"{warmup_words} words of presenter speech..."
            )

            _warmup_check_interval = 3.0
            _warmup_checks = 0
            while not self._stop_event.is_set():
                total_words = sum(
                    len(s.get("text", "").split())
                    for s in self.observation.transcript_segments
                )
                if total_words >= warmup_words:
                    logger.info(
                        f"Agent {self.agent_id}: warmup threshold met "
                        f"({total_words}/{warmup_words} words)"
                    )
                    break
                _warmup_checks += 1
                if _warmup_checks % 5 == 1:  # log every ~15s
                    logger.info(
                        f"Agent {self.agent_id}: warmup waiting — "
                        f"{total_words}/{warmup_words} words, "
                        f"{len(self.observation.transcript_segments)} segments"
                    )
                try:
                    await asyncio.wait_for(
                        self._new_input_event.wait(),
                        timeout=_warmup_check_interval,
                    )
                    self._new_input_event.clear()
                except asyncio.TimeoutError:
                    pass

            logger.info(
                f"Agent {self.agent_id}: warmup complete — "
                f"{len(self.observation.transcript_segments)} segments, "
                f"slide {self.observation.current_slide}"
            )
            self.state = AgentRunnerState.LISTENING
            await self._log_state("WARMING_UP", "LISTENING", "sufficient_context")

            while not self._stop_event.is_set():
                if self.state == AgentRunnerState.LISTENING:
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

                    # Skip if not enough context (same threshold as warmup)
                    if not self.observation.has_sufficient_context(min_words=warmup_words):
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

                            # Wait until moderator calls on us.
                            # Don't count time while another exchange is active —
                            # the moderator can't call on us during an exchange,
                            # so we should wait patiently.
                            self._called_on_event.clear()
                            _idle_wait_secs = 0.0
                            _max_idle_wait = 120.0  # only timeout after 120s of idle time
                            _timed_out = False
                            while not self._stop_event.is_set():
                                try:
                                    await asyncio.wait_for(
                                        self._called_on_event.wait(),
                                        timeout=2.0,
                                    )
                                    break  # called on!
                                except asyncio.TimeoutError:
                                    pass
                                # Only count toward timeout when no exchange is active
                                if not self.observation.exchange_active:
                                    _idle_wait_secs += 2.0
                                if _idle_wait_secs >= _max_idle_wait:
                                    _timed_out = True
                                    break

                            if _timed_out:
                                logger.info(
                                    f"Agent {self.agent_id} hand-raise timed out "
                                    f"after {_idle_wait_secs:.0f}s idle wait"
                                )
                                self.buffered_question = None
                                self.state = AgentRunnerState.LISTENING
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
                            self.state = AgentRunnerState.LISTENING
                    else:
                        self.state = AgentRunnerState.LISTENING

                elif self.state == AgentRunnerState.IN_EXCHANGE:
                    await asyncio.sleep(1)

                elif self.state == AgentRunnerState.COOLDOWN:
                    # Terminal state — session is ending
                    break

                elif self.state == AgentRunnerState.READY:
                    # Shouldn't normally reach here — wait is in IDLE→READY flow
                    await asyncio.sleep(0.5)

                else:
                    await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"AgentRunner {self.agent_id} loop error: {e}", exc_info=True)

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
        if self.question_count == 0 and transcript_growth >= 2:
            # First question after warmup — be aggressive
            result = True
            reason = "first_question"
        elif unchallenged:
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

        # Stream LLM → collect sentences → fire off TTS tasks in parallel
        sentences = []
        tts_tasks = []

        try:
            context_messages = [
                {"role": "user", "content": "Ask exactly ONE focused question now. Do not ask multiple questions or combine questions. Keep it to a single, direct question."}
            ]

            async def _stream_and_tts():
                async for sentence in self.llm.generate_question_streaming(
                    system_prompt=prompt,
                    context_messages=context_messages,
                ):
                    sentences.append(sentence)
                    # Start TTS for this sentence immediately (don't await)
                    task = asyncio.create_task(
                        self.tts.synthesize(self.agent_id, sentence, self.session_id)
                    )
                    tts_tasks.append(task)

            if self._llm_semaphore:
                async with self._llm_semaphore:
                    await _stream_and_tts()
            else:
                await _stream_and_tts()

        except Exception as e:
            logger.warning(
                f"LLM streaming failed for {self.agent_id}: {e}. Using fallback."
            )
            fallback_text = self._get_fallback_question()
            sentences = [fallback_text]
            tts_tasks = [asyncio.create_task(
                self.tts.synthesize(self.agent_id, fallback_text, self.session_id)
            )]

        # Wait for all TTS to complete
        audio_results = await asyncio.gather(*tts_tasks, return_exceptions=True)
        audio_urls = [u for u in audio_results if isinstance(u, str)]

        question_text = " ".join(sentences) if sentences else self._get_fallback_question()

        candidate = CandidateQuestion(
            agent_id=self.agent_id,
            text=question_text,
            target_claim=target_claim,
            slide_index=self.observation.current_slide,
            audio_url=audio_urls[0] if audio_urls else None,
            audio_urls=audio_urls,
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
                    "audio_urls": candidate.audio_urls,
                },
            )

        return candidate

    async def _deliver_question(self):
        """Called after moderator calls on us. Coordinator now handles delivery.

        This just updates internal bookkeeping. The actual question emission
        and transcript storage is done by the coordinator in _call_on_agent.
        """
        # State is already set to IN_EXCHANGE by _on_event(AGENT_CALLED_ON)
        self.question_count += 1
        await self._log_state("CALLED_ON", "IN_EXCHANGE", "coordinator delivered question")

    # --- Exchange follow-up (called by coordinator) ---

    async def handle_exchange_follow_up(
        self, exchange: Exchange, max_turns: int = 3
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
            turn_number=exchange.presenter_turn_count,
            max_turns=max_turns,
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
        logger.info(
            f"Exchange follow-up eval for {self.agent_id}: "
            f"verdict={verdict}, reasoning='{reasoning[:120]}'"
        )

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

            # Return text immediately — TTS will be handled async by coordinator
            return {
                "text": follow_up,
                "audio_url": None,
                "audio_urls": [],
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
