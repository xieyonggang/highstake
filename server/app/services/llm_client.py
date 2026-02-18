import logging
import re
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Abbreviations that should NOT be treated as sentence boundaries
_ABBREVIATIONS = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|Ave|Blvd|Gen|Gov|Sgt|Cpl|Pvt|Rev|Hon"
    r"|Inc|Corp|Ltd|Co|vs|etc|approx|dept|est|vol|U\.S|U\.K|E\.U|e\.g|i\.e)\.$",
    re.IGNORECASE,
)

# Sentence-ending punctuation followed by space or end-of-string
_SENTENCE_END = re.compile(r'([.?!])(?:\s|$)')


def split_sentences(text: str, min_chunk_len: int = 10) -> list[str]:
    """Split text into sentences at . ? ! boundaries.

    Skips common abbreviations and merges tiny fragments into the previous
    sentence to avoid sub-second audio chunks.
    """
    if not text or not text.strip():
        return []

    sentences: list[str] = []
    start = 0

    for m in _SENTENCE_END.finditer(text):
        end = m.end()
        candidate = text[start:end].strip()

        # Skip if this looks like an abbreviation
        if _ABBREVIATIONS.search(candidate):
            continue

        if candidate:
            # Merge tiny fragments into previous sentence
            if len(candidate) < min_chunk_len and sentences:
                sentences[-1] = sentences[-1] + " " + candidate
            else:
                sentences.append(candidate)
            start = end

    # Remaining text
    remainder = text[start:].strip()
    if remainder:
        if len(remainder) < min_chunk_len and sentences:
            sentences[-1] = sentences[-1] + " " + remainder
        else:
            sentences.append(remainder)

    return sentences if sentences else [text.strip()]


def _extract_first_sentence(buffer: str) -> str | None:
    """Extract the first complete sentence from buffer, or None if incomplete."""
    for m in _SENTENCE_END.finditer(buffer):
        candidate = buffer[: m.end()].strip()
        if _ABBREVIATIONS.search(candidate):
            continue
        if len(candidate) >= 10:
            return candidate
    return None


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

    async def generate_question_streaming(
        self,
        system_prompt: str,
        context_messages: list[dict],
    ) -> AsyncGenerator[str, None]:
        """Stream question generation, yielding each sentence as it completes."""
        user_text = "\n".join(m.get("content", "") for m in context_messages)
        buffer = ""

        stream = await self.client.aio.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.8,
            ),
        )
        async for chunk in stream:
            buffer += chunk.text or ""
            # Extract complete sentences as they arrive
            while True:
                sentence = _extract_first_sentence(buffer)
                if not sentence:
                    break
                yield sentence
                buffer = buffer[len(sentence) :].lstrip()

        # Yield any remaining text
        if buffer.strip():
            yield buffer.strip()

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
