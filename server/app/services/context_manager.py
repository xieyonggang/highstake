import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages the sliding context window for long sessions.

    Always includes: full slide manifest, current + adjacent slides,
    last 5 minutes of transcript, summarized earlier sections, key claims.
    """

    def __init__(self, max_transcript_chars: int = 8000):
        self.max_transcript_chars = max_transcript_chars
        self.key_claims: list[str] = []
        self.full_transcript: list[dict] = []  # All segments
        self.current_slide_index: int = 0

    def add_segment(self, segment: dict) -> None:
        """Add a new transcript segment. Extract key claims if they contain
        numbers, percentages, comparisons, or specific assertions."""
        self.full_transcript.append(segment)

        text = segment.get("text", "")
        if self._contains_key_claim(text):
            self.key_claims.append(text)

    def _contains_key_claim(self, text: str) -> bool:
        """Check if text contains numbers, percentages, or specific assertions."""
        patterns = [
            r'\d+%',           # percentages
            r'\$[\d,.]+',      # dollar amounts
            r'\d+[BMK]\b',     # billions/millions/thousands
            r'\d+x\b',        # multipliers
            r'will\s+\w+',    # future projections
            r'expect\w*',     # expectations
            r'project\w*',    # projections
            r'target\w*',     # targets
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def get_context_for_agent(
        self,
        agent_id: str,
        current_slide_index: int,
        deck_manifest: dict,
        elapsed_seconds: float,
    ) -> dict:
        """Return the assembled context payload for an agent's next question."""
        self.current_slide_index = current_slide_index

        # Get current slide info
        slides = deck_manifest.get("slides", [])
        current_slide = None
        if 0 <= current_slide_index < len(slides):
            current_slide = slides[current_slide_index]

        # Build transcript text with sliding window
        transcript_text = self._build_transcript_text(elapsed_seconds)

        return {
            "current_slide_text": self._format_slide(current_slide) if current_slide else "",
            "current_slide_title": current_slide.get("title", "") if current_slide else "",
            "current_slide_notes": current_slide.get("notes", "") if current_slide else "",
            "transcript_text": transcript_text,
            "key_claims": self.key_claims[-20:],  # Last 20 key claims
            "elapsed_seconds": elapsed_seconds,
        }

    def _build_transcript_text(self, elapsed_seconds: float) -> str:
        """Build transcript text with sliding window strategy."""
        if not self.full_transcript:
            return ""

        # If transcript is short enough, include everything
        full_text = self._format_transcript(self.full_transcript)
        if len(full_text) <= self.max_transcript_chars:
            return full_text

        # Otherwise, use sliding window:
        # 1. Summarize early segments
        # 2. Keep last 5 minutes in full
        five_min_ago = elapsed_seconds - 300

        recent = [s for s in self.full_transcript if s.get("start_time", 0) >= five_min_ago]
        older = [s for s in self.full_transcript if s.get("start_time", 0) < five_min_ago]

        parts = []

        # Add summarized older section
        if older:
            older_text = self._format_transcript(older)
            if len(older_text) > 2000:
                # Compress to key claims only
                parts.append("[Earlier in the presentation, the presenter discussed:]")
                for claim in self.key_claims[:10]:
                    parts.append(f"- {claim}")
                parts.append("")
            else:
                parts.append(older_text)

        # Add recent section in full
        if recent:
            parts.append("[Recent transcript:]")
            parts.append(self._format_transcript(recent))

        return "\n".join(parts)

    def _format_transcript(self, segments: list[dict]) -> str:
        """Format transcript segments into readable text."""
        lines = []
        for seg in segments:
            text = seg.get("text", "").strip()
            if text:
                lines.append(text)
        return "\n".join(lines)

    def _format_slide(self, slide: dict) -> str:
        """Format a slide's content for agent context."""
        parts = []
        if slide.get("title"):
            parts.append(f"Title: {slide['title']}")
        if slide.get("subtitle"):
            parts.append(f"Subtitle: {slide['subtitle']}")
        if slide.get("body_text"):
            parts.append(f"Content: {slide['body_text']}")
        return "\n".join(parts)
