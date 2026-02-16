import logging
import random
import time
from typing import Optional

from app.services.agent_prompts import (
    AGENT_NAMES,
    AGENT_ROLES,
    AGENT_TITLES,
    build_agent_prompt,
)
from app.services.llm_client import LLMClient
from app.services.context_manager import ContextManager
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)

# Fallback questions if Claude API fails
FALLBACK_QUESTIONS = {
    "skeptic": [
        "What's your contingency if these revenue projections fall short by 30%?",
        "What specific evidence supports these margin assumptions?",
        "How did you validate the TAM figures you're presenting?",
        "What happens if the regulatory environment shifts against us?",
    ],
    "analyst": [
        "Can you walk me through the methodology behind these estimates?",
        "What's the sample size and confidence interval for this data?",
        "I'd like to see the sensitivity analysis on your key assumptions.",
        "How does this compare to industry benchmarks?",
    ],
    "contrarian": [
        "What if a major incumbent enters this space with significantly more resources?",
        "Walk me through the scenario where everything goes wrong.",
        "You're assuming customers will change behavior. Why is this different from past attempts?",
        "I see a tension between your growth targets and profitability timeline. How do you reconcile that?",
    ],
}

# Question timing parameters per interaction mode
TIMING = {
    "section": {"min_gap": 0, "max_queue": 3, "batch": True},
    "hand-raise": {"min_gap": 15, "max_queue": 2, "batch": False},
    "interrupt": {"min_gap": 20, "max_queue": 1, "batch": False},
}


class AgentEngine:
    """Core orchestration engine for AI agent interactions."""

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
        self.context = ContextManager()
        self.current_slide = 0
        self.previous_questions: list[dict] = []
        self.last_question_time: float = 0
        self.session_start_time: float = time.time()
        self.question_count: int = 0
        self.last_agent: Optional[str] = None
        self.agent_question_counts: dict[str, int] = {
            "skeptic": 0,
            "analyst": 0,
            "contrarian": 0,
        }

    def _elapsed_seconds(self) -> float:
        return time.time() - self.session_start_time

    async def on_transcript_segment(self, segment: dict) -> None:
        """Called when a new transcript segment arrives from STT."""
        self.context.add_segment(segment)

        if self.config["interaction_mode"] == "interrupt":
            await self._evaluate_free_flow_question(segment)

    async def on_slide_change(self, slide_index: int) -> None:
        """Called when presenter advances slides."""
        old_slide = self.current_slide
        self.current_slide = slide_index

        mode = self.config["interaction_mode"]

        if mode == "section" and slide_index > old_slide:
            await self._trigger_section_qa()
        elif mode == "hand-raise":
            await self._evaluate_hand_raise()
        elif mode == "interrupt":
            # In free-flow, slide change can trigger a question sooner
            elapsed = self._elapsed_seconds()
            if elapsed - self.last_question_time >= 10:  # Reduced gap on slide change
                await self._evaluate_free_flow_question(None)

    async def _trigger_section_qa(self) -> None:
        """Section break mode: moderator announces Q&A, agents ask in order."""
        await self._emit_moderator("Let's pause for questions on this section.")

        agents = self._select_agents_for_section(max_count=TIMING["section"]["max_queue"])
        for agent_id in agents:
            await self._generate_and_emit_question(agent_id)

    async def _evaluate_hand_raise(self) -> None:
        """Hand-raise mode: evaluate if any agent has a pressing question."""
        elapsed = self._elapsed_seconds()
        if elapsed - self.last_question_time < TIMING["hand-raise"]["min_gap"]:
            return

        agent_id = self._select_next_agent()
        if agent_id:
            await self.emit("agent_hand_raise", {"agentId": agent_id})
            agent_name = AGENT_NAMES.get(agent_id, agent_id)
            await self._emit_moderator(f"I see {agent_name} has a question. Go ahead.")
            await self._generate_and_emit_question(agent_id)

    async def _evaluate_free_flow_question(self, segment: Optional[dict]) -> None:
        """Free-flow mode: check if enough time has passed for a new question."""
        elapsed = self._elapsed_seconds()
        min_gap = TIMING["interrupt"]["min_gap"]

        if elapsed - self.last_question_time < min_gap:
            return

        # Need at least some transcript to generate relevant questions
        if len(self.context.full_transcript) < 3:
            return

        agent_id = self._select_next_agent()
        if agent_id:
            await self._generate_and_emit_question(agent_id)

    async def _generate_and_emit_question(self, agent_id: str) -> None:
        """Build context, call Gemini, emit question event, optionally TTS."""
        context = self.context.get_context_for_agent(
            agent_id,
            self.current_slide,
            self.deck_manifest,
            self._elapsed_seconds(),
        )

        prompt = build_agent_prompt(
            agent_id=agent_id,
            intensity=self.config["intensity"],
            focus_areas=self.config.get("focus_areas", []),
            slide_index=self.current_slide,
            total_slides=self.deck_manifest.get("totalSlides", 6),
            slide_title=context.get("current_slide_title", ""),
            slide_content=context.get("current_slide_text", ""),
            slide_notes=context.get("current_slide_notes", ""),
            transcript=context.get("transcript_text", ""),
            previous_questions=[q["text"] for q in self.previous_questions],
            elapsed_time=self._elapsed_seconds(),
        )

        try:
            question_text = await self.llm.generate_question(
                system_prompt=prompt,
                context_messages=[{"role": "user", "content": "Ask your question now."}],
            )
        except Exception as e:
            logger.warning(f"Gemini API failed for {agent_id}: {e}. Using fallback.")
            question_text = self._get_fallback_question(agent_id)

        self.previous_questions.append({"agent_id": agent_id, "text": question_text})
        self.last_question_time = self._elapsed_seconds()
        self.last_agent = agent_id
        self.question_count += 1
        self.agent_question_counts[agent_id] = self.agent_question_counts.get(agent_id, 0) + 1

        # Store transcript entry
        await self._store_transcript_entry(agent_id, question_text)

        # Attempt TTS
        audio_url = None
        try:
            audio_url = await self.tts.synthesize(agent_id, question_text, session_id=self.session_id)
        except Exception as e:
            logger.warning(f"TTS failed for {agent_id}: {e}. Text-only.")

        await self.emit("agent_question", {
            "agentId": agent_id,
            "agentName": AGENT_NAMES.get(agent_id, agent_id),
            "agentRole": AGENT_ROLES.get(agent_id, ""),
            "agentTitle": AGENT_TITLES.get(agent_id, ""),
            "text": question_text,
            "audioUrl": audio_url,
            "slideRef": self.current_slide,
        })

    def _select_next_agent(self) -> Optional[str]:
        """Round-robin agent selection, weighted toward focus-area-relevant agents."""
        agents = ["skeptic", "analyst", "contrarian"]

        # Don't let the same agent ask twice in a row
        if self.last_agent:
            agents = [a for a in agents if a != self.last_agent]

        if not agents:
            agents = ["skeptic", "analyst", "contrarian"]

        # Weight toward agents whose focus aligns with selected focus areas
        focus_areas = set(self.config.get("focus_areas", []))
        weighted = []
        for agent in agents:
            weight = 1
            if agent == "skeptic" and focus_areas & {"Financial Projections", "Risk Assessment"}:
                weight = 2
            elif agent == "analyst" and focus_areas & {"Market Sizing", "Competitive Analysis", "Technical Feasibility"}:
                weight = 2
            elif agent == "contrarian" and focus_areas & {"Go-to-Market Strategy", "Timeline & Milestones", "Team & Execution"}:
                weight = 2
            weighted.extend([agent] * weight)

        return random.choice(weighted) if weighted else None

    def _select_agents_for_section(self, max_count: int) -> list[str]:
        """Select up to max_count agents for a section break Q&A window."""
        agents = ["skeptic", "analyst", "contrarian"]
        # Pick 1-2 agents per section to avoid overwhelming
        count = min(max_count, random.choice([1, 2]))
        selected = random.sample(agents, count)
        return selected

    async def _emit_moderator(self, text: str) -> None:
        """Emit a moderator message with optional TTS."""
        audio_url = None
        try:
            audio_url = await self.tts.synthesize("moderator", text, session_id=self.session_id)
        except Exception:
            pass

        await self._store_transcript_entry("moderator", text, entry_type="moderator")

        await self.emit("moderator_message", {
            "text": text,
            "audioUrl": audio_url,
            "agentName": AGENT_NAMES["moderator"],
            "agentRole": AGENT_ROLES["moderator"],
        })

    def _get_fallback_question(self, agent_id: str) -> str:
        """Return a fallback question if Claude API fails."""
        questions = FALLBACK_QUESTIONS.get(agent_id, [])
        if questions:
            # Use question count to avoid repeating
            idx = self.agent_question_counts.get(agent_id, 0) % len(questions)
            return questions[idx]
        return "Could you elaborate on that point?"

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
                entry_index = len(self.previous_questions) + 100  # Offset from presenter entries
                entry = TranscriptEntry(
                    session_id=self.session_id,
                    entry_index=entry_index,
                    speaker=f"agent_{agent_id}" if agent_id != "moderator" else "moderator",
                    speaker_name=AGENT_NAMES.get(agent_id, agent_id),
                    agent_role=AGENT_ROLES.get(agent_id),
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
