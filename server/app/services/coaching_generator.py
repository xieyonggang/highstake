import json
import logging
from typing import Optional

from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

COACHING_SYSTEM_PROMPT = """You are an executive presentation coach analyzing a boardroom practice session.
You have access to the full transcript, all agent questions and presenter responses, and the scoring results.

Generate a coaching report in JSON format with:
1. A moderator summary (150-250 words, written as Diana Chen, Chief of Staff, in first person).
   Cover: overall impression, biggest strength, most critical area for improvement,
   one specific tactical recommendation, and encouragement/next steps.
2. 3-5 specific strengths with examples from the session
3. 3-5 prioritized improvement areas (High/Medium/Low priority) with:
   - The area name
   - Specific detail explaining what happened and what to do differently
   - An approximate timestamp reference (in seconds from session start)

Respond ONLY with valid JSON matching this exact schema:
{
  "moderator_summary": "string",
  "strengths": ["string", "string"],
  "coaching_items": [
    {
      "area": "string",
      "priority": "high|medium|low",
      "detail": "string",
      "timestamp_ref": number
    }
  ]
}"""


class CoachingGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def generate(
        self,
        transcript: list[dict],
        scores: dict,
        config: dict,
        deck_manifest: dict,
    ) -> dict:
        """Generate the full coaching report using Claude."""
        session_context = self._build_session_context(
            transcript, scores, config, deck_manifest
        )

        response_text = await self.llm.generate_debrief(
            system_prompt=COACHING_SYSTEM_PROMPT,
            session_data=session_context,
            max_tokens=2000,
        )

        return self._parse_coaching_response(response_text)

    def _build_session_context(
        self,
        transcript: list[dict],
        scores: dict,
        config: dict,
        deck_manifest: dict,
    ) -> str:
        """Assemble all session data into a context string for Claude."""
        parts = []

        # Session configuration
        parts.append("## Session Configuration")
        parts.append(f"- Interaction mode: {config.get('interaction_mode', 'unknown')}")
        parts.append(f"- Intensity: {config.get('intensity', 'unknown')}")
        parts.append(f"- Focus areas: {', '.join(config.get('focus_areas', []))}")
        parts.append("")

        # Scores
        parts.append("## Scores")
        for key, value in scores.items():
            parts.append(f"- {key}: {value}/100")
        parts.append("")

        # Deck summary
        slides = deck_manifest.get("slides", [])
        if slides:
            parts.append("## Deck Summary")
            for s in slides[:20]:  # Limit to first 20 slides
                title = s.get("title", f"Slide {s.get('index', 0) + 1}")
                parts.append(f"- Slide {s.get('index', 0) + 1}: {title}")
            parts.append("")

        # Transcript
        parts.append("## Full Transcript")
        for entry in transcript:
            speaker = entry.get("speaker_name", entry.get("speaker", "Unknown"))
            text = entry.get("text", "")
            time_ref = entry.get("start_time", 0)
            parts.append(f"[{time_ref:.0f}s] {speaker}: {text}")
        parts.append("")

        return "\n".join(parts)

    def _parse_coaching_response(self, response_text: str) -> dict:
        """Parse Claude's JSON response. Handle malformed JSON gracefully."""
        try:
            # Try to extract JSON from the response
            # Claude sometimes wraps JSON in markdown code blocks
            text = response_text.strip()
            if text.startswith("```"):
                # Remove markdown code block
                lines = text.split("\n")
                text = "\n".join(
                    line for line in lines
                    if not line.strip().startswith("```")
                )

            data = json.loads(text)

            return {
                "moderator_summary": data.get("moderator_summary", ""),
                "strengths": data.get("strengths", []),
                "coaching_items": data.get("coaching_items", []),
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse coaching response as JSON: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")

            # Return a graceful fallback
            return {
                "moderator_summary": (
                    "Thank you for your presentation today. While I wasn't able to generate "
                    "a detailed analysis, your scores above reflect the key areas of strength "
                    "and improvement. I encourage you to review the individual scores and "
                    "practice the areas that scored below 70."
                ),
                "strengths": [
                    "Completed the full presentation session",
                    "Engaged with agent questions",
                ],
                "coaching_items": [
                    {
                        "area": "Overall Improvement",
                        "priority": "medium",
                        "detail": "Review the scoring breakdown above and focus on the lowest-scoring dimension in your next practice session.",
                        "timestamp_ref": 0,
                    }
                ],
            }
