import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages the sliding context window for long sessions.

    Tracks per-slide speech, builds a running presentation summary,
    and assembles rich context for each agent question including
    transcript text, key claims, and slide-segmented speech history.
    """

    def __init__(self, max_transcript_chars: int = 8000):
        self.max_transcript_chars = max_transcript_chars
        self.key_claims: list[str] = []
        self.full_transcript: list[dict] = []  # All segments
        self.current_slide_index: int = 0

        # Per-slide speech tracking: slide_index -> list of speech segments
        self.slide_speech: dict[int, list[str]] = {}
        # Running presentation summary built from completed slides
        self.presentation_summary: list[str] = []
        # Track which slides have been summarized
        self._summarized_slides: set[int] = set()

    def add_segment(self, segment: dict) -> None:
        """Add a new transcript segment. Extract key claims if they contain
        numbers, percentages, comparisons, or specific assertions.
        Also tracks speech per slide."""
        self.full_transcript.append(segment)

        text = segment.get("text", "")
        if not text.strip():
            return

        # Track speech for the current slide
        if self.current_slide_index not in self.slide_speech:
            self.slide_speech[self.current_slide_index] = []
        self.slide_speech[self.current_slide_index].append(text.strip())

        if self._contains_key_claim(text):
            self.key_claims.append(text)

    def on_slide_change(self, new_slide_index: int, deck_manifest: dict) -> None:
        """Called when the presenter advances slides. Summarizes the previous
        slide's speech into the running presentation summary."""
        old_slide = self.current_slide_index

        # Summarize the old slide before moving on
        if old_slide not in self._summarized_slides and old_slide in self.slide_speech:
            self._summarize_slide(old_slide, deck_manifest)

        self.current_slide_index = new_slide_index

    def _summarize_slide(self, slide_index: int, deck_manifest: dict) -> None:
        """Build a summary entry for a completed slide."""
        self._summarized_slides.add(slide_index)

        slides = deck_manifest.get("slides", [])
        slide_info = slides[slide_index] if 0 <= slide_index < len(slides) else None
        slide_title = slide_info.get("title", f"Slide {slide_index + 1}") if slide_info else f"Slide {slide_index + 1}"

        speech_texts = self.slide_speech.get(slide_index, [])
        if not speech_texts:
            return

        # Combine speech for this slide, truncate if very long
        combined = " ".join(speech_texts)
        if len(combined) > 500:
            combined = combined[:500] + "..."

        self.presentation_summary.append(
            f"[Slide {slide_index + 1}: {slide_title}] {combined}"
        )

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

        # Build presentation summary text
        presentation_summary_text = self._build_presentation_summary()

        # Get speech for the current slide
        current_slide_speech = self._get_current_slide_speech(current_slide_index)

        # Build all-slides context (brief overview of each slide)
        all_slides_context = self._build_all_slides_context(
            current_slide_index, deck_manifest
        )

        return {
            "current_slide_text": self._format_slide(current_slide) if current_slide else "",
            "current_slide_title": current_slide.get("title", "") if current_slide else "",
            "current_slide_notes": current_slide.get("notes", "") if current_slide else "",
            "transcript_text": transcript_text,
            "key_claims": self.key_claims[-20:],  # Last 20 key claims
            "elapsed_seconds": elapsed_seconds,
            "presentation_summary": presentation_summary_text,
            "current_slide_speech": current_slide_speech,
            "all_slides_context": all_slides_context,
        }

    def _build_presentation_summary(self) -> str:
        """Build the running presentation summary from completed slides."""
        if not self.presentation_summary:
            return ""
        return "\n".join(self.presentation_summary)

    def _get_current_slide_speech(self, slide_index: int) -> str:
        """Get what the presenter has said on the current slide."""
        speech_texts = self.slide_speech.get(slide_index, [])
        if not speech_texts:
            return ""
        combined = " ".join(speech_texts)
        # Limit to last 2000 chars for current slide
        if len(combined) > 2000:
            combined = "..." + combined[-2000:]
        return combined

    def _build_all_slides_context(
        self, current_slide_index: int, deck_manifest: dict
    ) -> str:
        """Build a brief overview of all slides with what was discussed on each."""
        slides = deck_manifest.get("slides", [])
        if not slides:
            return ""

        parts = []
        for i, slide in enumerate(slides):
            title = slide.get("title", f"Slide {i + 1}")
            marker = " <-- CURRENT" if i == current_slide_index else ""

            speech = self.slide_speech.get(i, [])
            if speech:
                # Summarize speech briefly
                combined = " ".join(speech)
                if len(combined) > 200:
                    combined = combined[:200] + "..."
                parts.append(f"  Slide {i + 1}: {title}{marker} — Presenter said: \"{combined}\"")
            else:
                if i <= current_slide_index:
                    parts.append(f"  Slide {i + 1}: {title}{marker} — (no speech recorded)")
                else:
                    parts.append(f"  Slide {i + 1}: {title} — (upcoming)")

        return "\n".join(parts)

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
