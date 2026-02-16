import logging
from typing import Optional

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
        max_tokens: int = 300,
    ) -> str:
        """Generate an agent question using Gemini.
        Uses gemini-2.5-flash for speed/cost balance during live sessions."""
        # Build user content from context messages
        user_text = "\n".join(m.get("content", "") for m in context_messages)

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                temperature=0.8,
            ),
        )
        return response.text

    async def generate_debrief(
        self,
        system_prompt: str,
        session_data: str,
        max_tokens: int = 2000,
    ) -> str:
        """Generate post-session analysis using Gemini."""
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=session_data,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                temperature=0.6,
            ),
        )
        return response.text
