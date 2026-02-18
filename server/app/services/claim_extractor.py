"""LLM-based claim extraction from presentation decks."""

import asyncio
import json
import logging
from typing import Optional

from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

CLAIM_EXTRACTION_PROMPT = """You are analyzing a presentation slide for challengeable claims.

Identify specific claims that a boardroom panel would want to scrutinize. Focus on:
- Financial claims (revenue, margins, growth rates, projections)
- Market claims (TAM, market share, competitive position)
- Timeline claims (delivery dates, milestones, launch dates)
- Capability claims (technical feasibility, team readiness)
- Competitive claims (differentiation, moat, advantages)

For each claim, extract:
- text: The exact or paraphrased claim
- type: One of "financial", "market", "timeline", "capability", "competitive"
- confidence: How specific/falsifiable the claim is (0.0 to 1.0)

Respond with a JSON array of claims. If no challengeable claims, return [].

Example:
[
  {"text": "We project 40% revenue growth in year 2", "type": "financial", "confidence": 0.9},
  {"text": "Our TAM is $5B", "type": "market", "confidence": 0.7}
]
"""


async def extract_claims_from_deck(
    llm: LLMClient,
    deck_manifest: dict,
) -> dict[int, list[dict]]:
    """Extract challengeable claims from each slide in parallel.

    Returns: {slide_index: [{"text": ..., "type": ..., "confidence": ...}]}
    """
    slides = deck_manifest.get("slides", [])
    if not slides:
        return {}

    tasks = []
    for i, slide in enumerate(slides):
        tasks.append(_extract_slide_claims(llm, i, slide))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    claims_by_slide: dict[int, list[dict]] = {}
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Claim extraction failed for slide {i}: {result}")
            continue
        if result:
            claims_by_slide[i] = result

    total = sum(len(c) for c in claims_by_slide.values())
    logger.info(f"Extracted {total} claims from {len(claims_by_slide)} slides")
    return claims_by_slide


async def _extract_slide_claims(
    llm: LLMClient,
    slide_index: int,
    slide: dict,
) -> list[dict]:
    """Extract claims from a single slide."""
    title = slide.get("title", "")
    body = slide.get("body_text", "")
    notes = slide.get("notes", "")

    content = f"Slide {slide_index + 1}: {title}\n{body}"
    if notes:
        content += f"\nSpeaker notes: {notes}"

    if len(content.strip()) < 20:
        return []

    try:
        from google.genai import types

        response = await llm.client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=content,
            config=types.GenerateContentConfig(
                system_instruction=CLAIM_EXTRACTION_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        text = (response.text or "").strip()
        claims = json.loads(text)
        if isinstance(claims, list):
            return claims
        return []
    except Exception as e:
        logger.warning(f"Claim extraction error for slide {slide_index}: {e}")
        return []
