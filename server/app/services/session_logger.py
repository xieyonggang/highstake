"""Session debug logger — writes human-readable Markdown files for agent behavior tracing.

Creates a per-session folder under data/sessions/{session_id}/ with timestamped
logs of every agent decision, LLM call, exchange, and event. Also copies each
panelist's persona and domain-knowledge templates into the session folder.

Fire-and-forget: errors are caught silently so logging never disrupts the live session.
"""

import asyncio
import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Path to agent templates (server/app/agents/templates)
_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "agents" / "templates"


def _fmt_elapsed(seconds: float) -> str:
    """Format elapsed seconds as MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _fmt_time(ts: str, elapsed: float) -> str:
    """Format a compact timestamp line: [MM:SS | HH:MM:SS UTC]."""
    try:
        dt = datetime.fromisoformat(ts)
        clock = dt.strftime("%H:%M:%S")
    except Exception:
        clock = ts
    return f"[{_fmt_elapsed(elapsed)} | {clock} UTC]"


def _dict_to_md(data: dict, indent: int = 0) -> str:
    """Convert a dict to readable markdown key-value lines."""
    lines = []
    prefix = "  " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}- **{k}:**")
            lines.append(_dict_to_md(v, indent + 1))
        elif isinstance(v, list):
            lines.append(f"{prefix}- **{k}:**")
            for item in v:
                if isinstance(item, dict):
                    lines.append(_dict_to_md(item, indent + 1))
                else:
                    lines.append(f"{prefix}  - {item}")
        else:
            lines.append(f"{prefix}- **{k}:** {v}")
    return "\n".join(lines)


class SessionLogger:
    """Writes human-readable Markdown debug logs to data/sessions/{session_id}/."""

    def __init__(self, session_id: str, base_dir: str = "./data"):
        self.session_id = session_id
        self.session_dir = os.path.join(base_dir, "sessions", session_id)
        self._start_time = time.time()
        self._init_dirs()

    def _init_dirs(self) -> None:
        """Create the folder structure for this session."""
        dirs = [
            self.session_dir,
            os.path.join(self.session_dir, "moderator"),
            os.path.join(self.session_dir, "presenter"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def _ensure_agent_dir(self, agent_id: str) -> None:
        """Create agent subfolder on first use."""
        agent_dir = os.path.join(self.session_dir, "agents", agent_id)
        os.makedirs(agent_dir, exist_ok=True)

    def _elapsed(self) -> float:
        return round(time.time() - self._start_time, 2)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _time_header(self) -> str:
        """Return a compact timestamp prefix for log entries."""
        return _fmt_time(self._timestamp(), self._elapsed())

    def _safe_serialize(self, obj: Any) -> Any:
        """Make objects JSON-serializable."""
        if isinstance(obj, dict):
            return {k: self._safe_serialize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._safe_serialize(v) for v in obj]
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        if hasattr(obj, "__dict__"):
            return self._safe_serialize(obj.__dict__)
        if hasattr(obj, "value"):  # Enum
            return obj.value
        return str(obj)

    def _append_sync(self, rel_path: str, text: str) -> None:
        """Synchronous file append (called in thread pool)."""
        full_path = os.path.join(self.session_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(text)

    def _write_file_sync(self, rel_path: str, content: str) -> None:
        """Synchronous file write (called in thread pool)."""
        full_path = os.path.join(self.session_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    async def _append(self, rel_path: str, text: str) -> None:
        """Append text to a file. Fire-and-forget."""
        try:
            await asyncio.to_thread(self._append_sync, rel_path, text)
        except Exception as e:
            logger.debug(f"SessionLogger write error: {e}")

    async def _write(self, rel_path: str, content: str) -> None:
        """Write (overwrite) a file. Fire-and-forget."""
        try:
            await asyncio.to_thread(self._write_file_sync, rel_path, content)
        except Exception as e:
            logger.debug(f"SessionLogger write error: {e}")

    # --- Agent persona/knowledge copying ---

    def copy_agent_templates(self, agent_ids: list[str]) -> None:
        """Copy persona.md and domain-knowledge.md into each agent's session folder."""
        if not _TEMPLATES_DIR.is_dir():
            logger.warning(f"Templates dir not found: {_TEMPLATES_DIR}")
            return

        for agent_id in agent_ids:
            agent_template_dir = _TEMPLATES_DIR / agent_id
            if not agent_template_dir.is_dir():
                continue

            dest_dir = os.path.join(self.session_dir, "agents", agent_id)
            os.makedirs(dest_dir, exist_ok=True)

            for md_file in agent_template_dir.glob("*.md"):
                dest_path = os.path.join(dest_dir, md_file.name)
                try:
                    shutil.copy2(str(md_file), dest_path)
                except Exception as e:
                    logger.debug(f"Failed to copy {md_file} -> {dest_path}: {e}")

        # Also copy moderator templates
        moderator_dir = _TEMPLATES_DIR / "moderator"
        if moderator_dir.is_dir():
            dest_dir = os.path.join(self.session_dir, "moderator")
            os.makedirs(dest_dir, exist_ok=True)
            for md_file in moderator_dir.glob("*.md"):
                dest_path = os.path.join(dest_dir, md_file.name)
                try:
                    shutil.copy2(str(md_file), dest_path)
                except Exception as e:
                    logger.debug(f"Failed to copy {md_file} -> {dest_path}: {e}")

    # --- Convenience methods ---

    async def log_session_config(
        self,
        config: dict,
        deck_manifest: dict,
        agents: list[str],
    ) -> None:
        """Write session-config.md with initial config snapshot."""
        slide_titles = [
            s.get("title", "(untitled)")
            for s in deck_manifest.get("slides", [])
        ]
        slides_list = "\n".join(
            f"  {i+1}. {t}" for i, t in enumerate(slide_titles)
        ) or "  (no slides)"

        content = f"""# Session Config

**Session ID:** `{self.session_id}`
**Started:** {self._timestamp()}

## Settings

- **Interaction mode:** {config.get('interaction_mode', 'N/A')}
- **Intensity:** {config.get('intensity', 'N/A')}
- **Agents:** {', '.join(agents)}
- **Focus areas:** {', '.join(config.get('focus_areas', [])) or 'none'}

## Deck

- **Filename:** {deck_manifest.get('filename', 'N/A')}
- **Total slides:** {deck_manifest.get('totalSlides', 'N/A')}
- **Slides:**
{slides_list}
"""
        # Copy agent templates into session folder
        self.copy_agent_templates(agents)

        await self._write("session-config.md", content)

    async def log_timeline_event(
        self, event_type: str, data: dict, source: str
    ) -> None:
        """Append to timeline.md — every event in chronological order."""
        entry = f"{self._time_header()} **{event_type}** from `{source}`"
        # Add key data inline if small
        serialized = self._safe_serialize(data)
        compact = {k: v for k, v in serialized.items() if v is not None}
        if compact:
            # Keep it concise — one-liner for simple data
            pairs = ", ".join(f"{k}={v}" for k, v in compact.items())
            if len(pairs) < 200:
                entry += f" — {pairs}"
        entry += "\n"
        await self._append("timeline.md", entry)

    async def log_transcript(self, segment: dict) -> None:
        """Log a final transcript segment."""
        text = segment.get("text", "")
        conf = segment.get("confidence")
        conf_str = f" (confidence: {conf:.2f})" if conf else ""
        entry = f"{self._time_header()} {text}{conf_str}\n"
        await self._append("transcript.md", entry)

    async def log_claims(self, claims_by_slide: dict) -> None:
        """Write claims.md with extracted claims organized by slide."""
        lines = [f"# Extracted Claims\n\n**Generated:** {self._timestamp()}\n"]
        serialized = self._safe_serialize(claims_by_slide)
        for slide_idx in sorted(serialized.keys(), key=lambda x: int(x)):
            claims = serialized[slide_idx]
            lines.append(f"\n## Slide {slide_idx}\n")
            if not claims:
                lines.append("_(no claims)_\n")
                continue
            for claim in claims:
                if isinstance(claim, dict):
                    text = claim.get("text", str(claim))
                    cat = claim.get("category", "")
                    cat_str = f" `[{cat}]`" if cat else ""
                    lines.append(f"- {text}{cat_str}")
                else:
                    lines.append(f"- {claim}")
            lines.append("")
        await self._write("claims.md", "\n".join(lines))

    # --- Agent-specific ---

    async def log_agent_state(
        self,
        agent_id: str,
        old_state: str,
        new_state: str,
        reason: str = "",
    ) -> None:
        """Log agent state machine transition."""
        self._ensure_agent_dir(agent_id)
        reason_str = f" — {reason}" if reason else ""
        entry = f"{self._time_header()} `{old_state}` → `{new_state}`{reason_str}\n"
        await self._append(f"agents/{agent_id}/state-changes.md", entry)

    async def log_agent_decision(
        self,
        agent_id: str,
        should_ask: bool,
        heuristics: dict,
    ) -> None:
        """Log should-ask evaluation decision with inputs."""
        self._ensure_agent_dir(agent_id)
        verdict = "**YES — should ask**" if should_ask else "no"
        h = self._safe_serialize(heuristics)
        details = ", ".join(f"{k}={v}" for k, v in h.items())
        entry = f"{self._time_header()} Decision: {verdict} | {details}\n"
        await self._append(f"agents/{agent_id}/decisions.md", entry)

    async def log_agent_context(
        self,
        agent_id: str,
        context: dict,
    ) -> None:
        """Log the context window snapshot sent to LLM."""
        self._ensure_agent_dir(agent_id)
        ctx = self._safe_serialize(context)
        lines = [
            f"\n---\n### Context Snapshot {self._time_header()}\n",
            f"- **Slide:** {ctx.get('current_slide_title', 'N/A')} (#{ctx.get('slide_index', '?')})",
            f"- **Slide text:** {(ctx.get('current_slide_text', '') or '')[:200]}...",
        ]
        transcript = ctx.get("transcript_text", "")
        if transcript:
            lines.append(f"\n**Recent transcript:**\n> {transcript[:500]}")
        lines.append("")
        await self._append(f"agents/{agent_id}/context-snapshots.md", "\n".join(lines))

    async def log_agent_question(
        self,
        agent_id: str,
        system_prompt: str,
        llm_response: str,
        candidate: Optional[dict] = None,
    ) -> None:
        """Log LLM prompt, response, and resulting candidate question."""
        self._ensure_agent_dir(agent_id)
        c = self._safe_serialize(candidate) if candidate else {}
        lines = [
            f"\n---\n### Question Generated {self._time_header()}\n",
            f"**Slide:** {c.get('slide_index', '?')}",
            f"**Target claim:** {c.get('target_claim', 'none')}\n",
            "**Question:**",
            f"> {llm_response}\n",
            f"**Audio:** {c.get('audio_url', 'none')}\n",
            "<details><summary>Full system prompt</summary>\n",
            f"```\n{system_prompt}\n```",
            "</details>\n",
        ]
        await self._append(f"agents/{agent_id}/questions.md", "\n".join(lines))

    async def log_agent_exchange(
        self,
        agent_id: str,
        event_type: str,
        data: dict,
    ) -> None:
        """Log exchange event (start, presenter_response, follow_up, resolved)."""
        self._ensure_agent_dir(agent_id)
        d = self._safe_serialize(data)

        if event_type == "presenter_response":
            entry = (
                f"{self._time_header()} **Presenter responded** (turn {d.get('turn', '?')}):\n"
                f"> {d.get('text', '')}\n\n"
            )
        elif event_type == "follow_up_eval":
            entry = (
                f"{self._time_header()} **Follow-up assessment** — "
                f"verdict: `{d.get('verdict', '?')}`, "
                f"turns: {d.get('turn_count', '?')}\n"
                f"Reasoning: {d.get('reasoning', 'N/A')}\n\n"
            )
        elif event_type == "resolved":
            turns_text = ""
            for t in d.get("turns", []):
                speaker = t.get("speaker", "?")
                turns_text += f"  - **{speaker}:** {t.get('text', '')}\n"
            entry = (
                f"\n---\n### Exchange Resolved {self._time_header()}\n\n"
                f"- **Outcome:** `{d.get('outcome', '?')}`\n"
                f"- **Turns:** {d.get('turn_count', '?')}\n"
                f"- **Reasoning:** {d.get('reasoning', 'N/A')}\n\n"
                f"**Transcript:**\n{turns_text}\n"
            )
        else:
            entry = f"{self._time_header()} **{event_type}** — {d}\n\n"

        await self._append(f"agents/{agent_id}/exchanges.md", entry)

    # --- Moderator ---

    async def log_moderator(self, action: str, data: dict) -> None:
        """Log moderator action (transition, bridge_back, time_warning)."""
        d = self._safe_serialize(data)
        details = ", ".join(f"{k}={v}" for k, v in d.items())
        entry = f"{self._time_header()} **{action}** — {details}\n"
        await self._append("moderator/actions.md", entry)

    async def log_queue_decision(
        self,
        queue_snapshot: list[dict],
        selected_agent: Optional[str],
        scores: Optional[list[dict]] = None,
    ) -> None:
        """Log hand-raise queue state and selection decision."""
        queue_str = ", ".join(
            f"{q.get('agent_id', '?')} (rel={q.get('relevance', '?')})"
            for q in queue_snapshot
        ) or "(empty after selection)"
        scores_str = ""
        if scores:
            scores_str = " | Scores: " + ", ".join(
                f"{s.get('agent_id', '?')}={s.get('score', '?')}"
                for s in scores
            )
        entry = (
            f"{self._time_header()} **Selected: `{selected_agent}`** "
            f"from queue [{queue_str}]{scores_str}\n"
        )
        await self._append("moderator/queue-decisions.md", entry)

    # --- Presenter ---

    async def log_presenter_profile(self, profile: dict) -> None:
        """Log presenter profile update."""
        p = self._safe_serialize(profile)
        entry = (
            f"\n---\n### Profile Update {self._time_header()}\n\n"
            f"{_dict_to_md(p)}\n"
        )
        await self._append("presenter/profile-updates.md", entry)
