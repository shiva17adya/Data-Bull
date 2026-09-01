#!/usr/bin/env python3
"""
Integration example for the Person 4 module.

Run it:

    python integration_example.py

It walks through five scenarios using only the bundled mocks:

    1. Happy path, conservative user
    2. Same market input, aggressive user  -> different recommendation
    3. Scenario A: sentiment agent fails
    4. Scenario B: RAG returns nothing
    5. Scenario C: incomplete market data

Person 5: the only import you need is `from app import analyze`.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import analyze  # noqa: E402
from app.adapters import (  # noqa: E402
    MockMarketSignalProvider,
    MockProfileProvider,
    MockRAGProvider,
)
from app.schemas.models import AnalysisResult  # noqa: E402

LINE = "=" * 78


def show(title: str, result: AnalysisResult, *, trace: bool = False) -> None:
    print(f"\n{LINE}\n{title}\n{LINE}")
    print(
        f"  signal         : {result.final_signal.value} "
        f"(weighted score {result.directional_score:+.2f})"
    )
    print(f"  confidence     : {result.confidence:.2f}")
    print(f"  recommendation : {result.recommendation.value}")
    print(f"  risk level     : {result.risk_level.value}")
    print(f"  data quality   : {result.data_quality.value}")
    print(f"  failed agents  : {result.failed_agents or 'none'}")
    print(f"  latency        : {result.total_latency_ms} ms")

    print("\n  agents:")
    for agent in result.agent_outputs:
        print(
            f"    - {agent.agent:<12} {agent.status.value:<17} "
            f"{agent.signal.value:<8} conf={agent.confidence:.2f} "
            f"quality={agent.data_quality.value:<6} {agent.latency_ms}ms"
        )
        if agent.errors:
            print(f"        error: {agent.errors[0]}")

    print("\n  reasoning:")
    for line in result.reasoning:
        print(f"    • {line}")

    if result.sources:
        print("\n  cited sources:")
        for source in result.sources[:4]:
            label = f"{source.source}" + (f" — {source.section}" if source.section else "")
            print(f"    • {label}")
        if len(result.sources) > 4:
            print(f"    • … and {len(result.sources) - 4} more")
    else:
        print("\n  cited sources: none (no fabricated citations)")

    print("\n  personalization:")
    for line in result.personalization:
        print(f"    • {line}")

    print("\n  risk factors:")
    for line in result.risk_factors:
        print(f"    • {line}")

    if trace:
        print("\n  reasoning trace (this is what the frontend renders):")
        for event in result.reasoning_trace:
            print(f"    {event.step}. [{event.stage}] {event.summary}")


async def main() -> None:
    market_provider = MockMarketSignalProvider()
    rag_provider = MockRAGProvider()
    profile_provider = MockProfileProvider()

    # Inputs a teammate would normally hand over.
    market_data = await market_provider.get_signals("RELIANCE")
    rag_context = await rag_provider.retrieve("RELIANCE", "RELIANCE outlook and risks")
    conservative = await profile_provider.get_profile("demo_conservative")
    aggressive = await profile_provider.get_profile("demo_aggressive")

    # ---- 1 & 2: personalization on identical market input ---------------
    result_conservative = await analyze("RELIANCE", market_data, rag_context, conservative)
    show("1. HAPPY PATH — conservative user (Ananya)", result_conservative, trace=True)

    result_aggressive = await analyze("RELIANCE", market_data, rag_context, aggressive)
    show("2. SAME MARKET INPUT — aggressive user (Karthik)", result_aggressive)

    print(f"\n{LINE}")
    print("PERSONALIZATION CHECK — identical market data, identical agent signals")
    print(LINE)
    print(
        f"  market signal (both users): {result_conservative.final_signal.value} "
        f"/ score {result_conservative.directional_score:+.2f}"
    )
    print(f"  conservative -> {result_conservative.recommendation.value}")
    print(f"  aggressive   -> {result_aggressive.recommendation.value}")
    print("  The directional signal is identical; only the recommendation differs.")

    # ---- 3: Scenario A, sentiment feed dies ------------------------------
    broken_market = {k: v for k, v in market_data.items() if k != "sentiment"}
    show(
        "3. DEGRADED — Scenario A: no sentiment feed",
        await analyze("RELIANCE", broken_market, rag_context, conservative),
    )

    # ---- 4: Scenario B, empty retrieval ----------------------------------
    show(
        "4. DEGRADED — Scenario B: RAG returns no documents",
        await analyze("RELIANCE", market_data, {"chunks": []}, conservative),
    )

    # ---- 5: Scenario C, partial market feed -------------------------------
    degraded_market = await market_provider.get_signals("RELIANCE_DEGRADED")
    show(
        "5. DEGRADED — Scenario C: incomplete market data",
        await analyze("RELIANCE", degraded_market, rag_context, conservative),
    )

    # ---- JSON handoff -----------------------------------------------------
    payload = result_aggressive.to_frontend_dict()
    print(f"\n{LINE}\nJSON HANDOFF (what the API layer returns)\n{LINE}")
    print(json.dumps(payload, indent=2)[:900] + "\n  … truncated")
    print(f"\n  top-level keys: {sorted(payload.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
