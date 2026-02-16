import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for the Anthropic Claude API."""

    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=api_key)

    async def generate_question(
        self,
        system_prompt: str,
        context_messages: list[dict],
        max_tokens: int = 300,
    ) -> str:
        """Generate an agent question using Claude.
        Uses claude-sonnet for speed/cost balance during live sessions."""
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=context_messages,
        )
        return response.content[0].text

    async def generate_debrief(
        self,
        system_prompt: str,
        session_data: str,
        max_tokens: int = 2000,
    ) -> str:
        """Generate post-session analysis using Claude."""
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": session_data}],
        )
        return response.content[0].text
