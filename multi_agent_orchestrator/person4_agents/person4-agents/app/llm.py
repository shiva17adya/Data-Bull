"""
Thin, optional wrapper around the Anthropic SDK.

Design rule for the hackathon: the LLM is an *enhancement*, never a
dependency. Every agent computes a deterministic signal first. If the LLM is
enabled and returns valid JSON, its narrative reasoning is used. If it is
disabled, unreachable, slow, or returns malformed output, the deterministic
result stands and the agent still succeeds.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Optional

from app.config import settings

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK.search(cleaned)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


async def structured_completion(
    system: str,
    prompt: str,
    *,
    max_tokens: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Ask Claude for a JSON object. Returns None on any problem at all."""
    if not settings.llm_available:
        return None
    try:
        from anthropic import AsyncAnthropic
    except ImportError:  # pragma: no cover - SDK not installed
        return None

    try:
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await asyncio.wait_for(
            client.messages.create(
                model=settings.anthropic_model,
                max_tokens=max_tokens or settings.llm_max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=settings.llm_timeout_s,
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        return _extract_json(text)
    except Exception:
        # Deliberately broad: a hackathon demo must not die because of a
        # network blip. The caller falls back to deterministic reasoning.
        return None
