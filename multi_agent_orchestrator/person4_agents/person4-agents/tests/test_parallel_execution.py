"""
Test 4: parallel execution.

Two independent proofs that the orchestrator runs agents concurrently:

1. Wall-clock: three agents that each sleep 0.30s finish in well under the
   0.90s a sequential run would take.
2. Interleaving: every agent starts before any agent finishes.
"""

from __future__ import annotations

import asyncio
import time

from app.agents.base_agent import BaseAgent
from app.orchestration.orchestrator import Orchestrator
from app.schemas.models import AgentOutput, AgentStatus, DataQuality, Signal

SLEEP = 0.30
TOLERANCE = 0.25  # generous headroom for CI noise


class SlowAgent(BaseAgent):
    """Records when it starts and stops so overlap can be verified."""

    def __init__(self, name: str, timeline: list[tuple[str, str, float]]):
        super().__init__()
        self.name = name
        self.timeline = timeline

    async def analyze(self, symbol: str, context: dict) -> AgentOutput:
        self.timeline.append((self.name, "start", time.perf_counter()))
        await asyncio.sleep(SLEEP)
        self.timeline.append((self.name, "end", time.perf_counter()))
        return AgentOutput(
            agent=self.name,
            status=AgentStatus.SUCCESS,
            signal=Signal.BULLISH,
            confidence=0.6,
            reasoning=[f"{self.name} slept {SLEEP}s"],
            data_quality=DataQuality.HIGH,
        )


async def test_agents_run_concurrently_not_sequentially(market_data, rag_context,
                                                        conservative_profile):
    timeline: list[tuple[str, str, float]] = []
    agents = [SlowAgent(name, timeline) for name in ("technical", "fundamental", "sentiment")]
    orchestrator = Orchestrator(agents=agents)

    started = time.perf_counter()
    result = await orchestrator.run(
        "RELIANCE", market_data, rag_context, conservative_profile
    )
    elapsed = time.perf_counter() - started

    sequential = SLEEP * len(agents)

    assert elapsed < SLEEP + TOLERANCE, (
        f"took {elapsed:.3f}s — expected roughly {SLEEP}s for concurrent execution"
    )
    assert elapsed < sequential * 0.6, (
        f"took {elapsed:.3f}s, close to the sequential {sequential:.2f}s"
    )
    assert len(result.agent_outputs) == 3


async def test_all_agents_overlap_in_time():
    timeline: list[tuple[str, str, float]] = []
    agents = [SlowAgent(name, timeline) for name in ("technical", "fundamental", "sentiment")]
    orchestrator = Orchestrator(agents=agents)

    await orchestrator.run("RELIANCE", {"indicators": {}}, {"chunks": []}, {})

    starts = [t for (_, event, t) in timeline if event == "start"]
    ends = [t for (_, event, t) in timeline if event == "end"]

    assert len(starts) == 3 and len(ends) == 3
    # Concurrency proof: the last agent begins before the first one finishes.
    assert max(starts) < min(ends), "agents did not overlap — execution was sequential"


async def test_slow_agent_does_not_block_fast_agents(market_data, rag_context,
                                                     conservative_profile):
    """A hung agent is bounded by its timeout; the others still deliver."""

    class HangingAgent(BaseAgent):
        name = "sentiment"

        async def analyze(self, symbol: str, context: dict) -> AgentOutput:
            await asyncio.sleep(10)
            raise AssertionError("should have timed out")

    from app.agents import FundamentalAgent, TechnicalAgent

    orchestrator = Orchestrator(
        agents=[TechnicalAgent(), FundamentalAgent(), HangingAgent(timeout_s=0.2)]
    )

    started = time.perf_counter()
    result = await orchestrator.run(
        "RELIANCE", market_data, rag_context, conservative_profile
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0, "a hung agent must not stall the pipeline"
    assert "sentiment" in result.failed_agents
    statuses = {o.agent: o.status for o in result.agent_outputs}
    assert statuses["technical"] == AgentStatus.SUCCESS
    assert statuses["fundamental"] == AgentStatus.SUCCESS
    assert statuses["sentiment"] == AgentStatus.FAILED
