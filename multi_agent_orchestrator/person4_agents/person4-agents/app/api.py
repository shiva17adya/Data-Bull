"""
Public integration surface for this module.

Person 5 only needs these two functions. Everything else is internal.

    from app import analyze            # async
    from app import analyze_sync       # blocking convenience wrapper
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from app.adapters import (
    MarketSignalProvider,
    ProfileProvider,
    RAGProvider,
)
from app.orchestration.orchestrator import Orchestrator
from app.schemas.models import AnalysisResult, UserProfile


async def analyze(
    symbol: str,
    market_data: Optional[dict[str, Any]] = None,
    rag_context: Optional[dict[str, Any]] = None,
    user_profile: Optional[dict[str, Any] | UserProfile] = None,
    *,
    market_provider: Optional[MarketSignalProvider] = None,
    rag_provider: Optional[RAGProvider] = None,
    profile_provider: Optional[ProfileProvider] = None,
    query: str = "",
) -> AnalysisResult:
    """Run the full multi-agent analysis for one symbol and one user.

    Args:
        symbol: Ticker, e.g. "RELIANCE".
        market_data: Pre-computed indicators from the signal engine. If None,
            `market_provider` is used.
        rag_context: Retrieved document chunks. If None, `rag_provider` is used.
        user_profile: Risk profile + portfolio. If None, `profile_provider`
            is used; if that is also None, neutral defaults apply.
        market_provider / rag_provider / profile_provider: Optional adapter
            implementations, used only for the arguments left as None.
        query: Optional retrieval query passed to the RAG provider.

    Returns:
        `AnalysisResult` — call `.to_frontend_dict()` for plain JSON.

    Never raises for data problems: missing or malformed inputs degrade the
    result (lower confidence, populated `failed_agents`) instead of crashing.
    """
    orchestrator = Orchestrator(
        market_provider=market_provider,
        rag_provider=rag_provider,
        profile_provider=profile_provider,
    )
    return await orchestrator.run(
        symbol=symbol,
        market_data=market_data,
        rag_context=rag_context,
        user_profile=user_profile,
        query=query,
    )


def analyze_sync(*args: Any, **kwargs: Any) -> AnalysisResult:
    """Blocking wrapper for callers that are not async (scripts, Flask, etc.).

    Do not call this from inside a running event loop — use `await analyze()`.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(analyze(*args, **kwargs))
    raise RuntimeError(
        "analyze_sync() cannot be called from a running event loop; use 'await analyze(...)'."
    )
