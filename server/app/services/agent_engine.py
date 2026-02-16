import logging
import random
import time
import glob
import os
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

# Fallback questions if Agent API fails
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
    "technologist": [
        "What's your technical architecture for handling 10x scale? Have you load-tested these assumptions?",
        "You mentioned a 6-month build timeline. What's your biggest technical risk that could derail that?",
        "Are you building this in-house or buying? What's the build-vs-buy analysis here?",
        "How are you handling data security and compliance at the infrastructure level?",
    ],
    "coo": [
        "What does the operational rollout look like? Walk me through the first 90 days.",
        "You'll need significant headcount to execute this. What's your hiring timeline and where are the bottlenecks?",
        "What are the key operational dependencies that could delay delivery?",
        "How does this scale operationally? What breaks at 10x volume?",
    ],
    "ceo": [
        "How does this fit into our broader three-year strategic vision?",
        "If we fund this, what are we saying no to? What's the opportunity cost?",
        "How do we communicate this to the board and key stakeholders?",
        "What's our competitive moat here and how durable is it over 5 years?",
    ],
    "cio": [
        "What's the expected IRR on this investment and how does it compare to our hurdle rate?",
        "Walk me through the downside scenario. What's our maximum capital at risk?",
        "What's the payback period and how sensitive is it to your key assumptions?",
        "How does this fit within our current capital allocation framework?",
    ],
    "chro": [
        "Do we have the talent in-house to execute this, or are we entirely dependent on new hires?",
        "What's the retention risk for the key people driving this initiative?",
        "How does this impact the existing team's workload and morale?",
        "What organizational changes are needed and how do you plan to manage that transition?",
    ],
    "cco": [
        "What's our regulatory exposure here? Have we run this by legal?",
        "How does this affect our corporate reputation if it doesn't go as planned?",
        "Are there any ESG or governance implications the board should be aware of?",
        "What compliance frameworks apply and are we confident we can meet them on this timeline?",
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
        self.active_agents: list[str] = config.get("agents", ["skeptic", "analyst", "contrarian"])
        self.agent_question_counts: dict[str, int] = {
            a: 0 for a in self.active_agents
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
        """Round-robin agent selection from active agents."""
        agents = list(self.active_agents)

        # Don't let the same agent ask twice in a row
        if self.last_agent and len(agents) > 1:
            agents = [a for a in agents if a != self.last_agent]

        if not agents:
            agents = list(self.active_agents)

        # Weight toward agents who have asked fewer questions
        if agents:
            min_count = min(self.agent_question_counts.get(a, 0) for a in agents)
            weighted = [a for a in agents if self.agent_question_counts.get(a, 0) == min_count]
            return random.choice(weighted)

        return None

    def _select_agents_for_section(self, max_count: int) -> list[str]:
        """Select up to max_count agents for a section break Q&A window."""
        agents = list(self.active_agents)
        # Pick 1-2 agents per section to avoid overwhelming
        count = min(max_count, len(agents), random.choice([1, 2]))
        selected = random.sample(agents, count)
        return selected

    async def _emit_moderator(self, text: str, is_static: bool = False) -> None:
        """Emit a moderator message using static audio file."""
        audio_url = None
        
        # Check for static audio file matching moderator*.wav in app/resources/common_assets
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        resources_dir = os.path.join(base_dir, "resources")
        common_assets_dir = os.path.join(resources_dir, "common_assets")
        
        moderator_pattern = os.path.join(common_assets_dir, "moderator*.wav")
        moderator_files = glob.glob(moderator_pattern)
        
        if moderator_files:
            # Use the first matching file, sorted to be deterministic
            moderator_files.sort()
            selected_file = moderator_files[0]
            
            # Make path relative to resources_dir for serving via /api/resources/
            rel_path = os.path.relpath(selected_file, resources_dir)
            
            # Ensure forward slashes for URL
            rel_path = rel_path.replace(os.sep, '/')
            audio_url = f"/api/resources/{rel_path}"
            logger.info(f"Using static moderator audio: {audio_url}")
        else:
            logger.warning(f"No static moderator audio found in {common_assets_dir}")

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
