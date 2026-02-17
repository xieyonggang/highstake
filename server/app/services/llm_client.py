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
