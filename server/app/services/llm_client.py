import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for the Google Gemini API."""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def generate_question(
        self,
        system_prompt: str,
        context_messages: list[dict],
    ) -> str:
        """Generate an agent question using Gemini.
        Uses gemini-2.5-flash for speed/cost balance during live sessions."""
        user_text = "\n".join(m.get("content", "") for m in context_messages)

        response = await self.client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.8,
            ),
        )

        text = (response.text or "").strip()
        finish = getattr(
            response.candidates[0], "finish_reason", None
        ) if response.candidates else None
        logger.info(
            f"LLM response: finish_reason={finish}, "
            f"len={len(text)}, text='{text[:200]}'"
        )
        return text

    async def evaluate_response(
        self,
        system_prompt: str,
        exchange_text: str,
    ) -> dict:
        """Evaluate a presenter's response, returning JSON verdict.

        Returns: {"verdict": "SATISFIED"|"FOLLOW_UP"|"ESCALATE",
                  "reasoning": str, "follow_up": str|None}
        """
        import json

        response = await self.client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=exchange_text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )

        text = (response.text or "").strip()
        logger.info(f"Evaluation response: {text[:300]}")

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse evaluation JSON: {text[:200]}")
            result = {"verdict": "SATISFIED", "reasoning": "Parse error", "follow_up": None}

        return result

    async def generate_debrief(
        self,
        system_prompt: str,
        session_data: str,
        max_tokens: int = 2000,
    ) -> str:
        """Generate post-session analysis using Gemini."""
        response = await self.client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=session_data,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                temperature=0.6,
            ),
        )
        return response.text
