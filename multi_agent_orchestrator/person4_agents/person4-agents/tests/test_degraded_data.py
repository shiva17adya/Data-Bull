"""
Tests 7 and 8: degraded-data behaviour.

Scenario A — sentiment agent fails outright.
Scenario B — RAG returns no documents.
Scenario C — market data is incomplete.
Scenario D — agents disagree (see test_synthesis.py).

The pipeline must never crash, never fabricate a citation, and never claim
high confidence on thin data.
"""

from __future__ import annotations

from app.agents import FundamentalAgent, SentimentAgent, TechnicalAgent
from app.agents.base_agent import BaseAgent
from app.orchestration.orchestrator import Orchestrator
from app.schemas.models import AgentOutput, AgentStatus, DataQuality, FinalSignal


class ExplodingAgent(BaseAgent):
    """Scenario A: an agent that raises mid-analysis."""

    name = "sentiment"

    async def analyze(self, symbol: str, context: dict) -> AgentOutput:
        raise ConnectionError("news feed unreachable")


class TestScenarioA_FailedAgent:
    async def test_pipeline_survives_agent_crash(self, market_data, rag_context,
                                                 conservative_profile):
        orchestrator = Orchestrator(
            agents=[TechnicalAgent(), FundamentalAgent(), ExplodingAgent()]
        )
        result = await orchestrator.run(
            "RELIANCE", market_data, rag_context, conservative_profile
        )

        assert result.final_signal in set(FinalSignal)
        assert "sentiment" in result.failed_agents
        assert len(result.agent_outputs) == 3

        sentiment = next(o for o in result.agent_outputs if o.agent == "sentiment")
        assert sentiment.status == AgentStatus.FAILED
        assert sentiment.confidence == 0.0
        assert sentiment.errors and "ConnectionError" in sentiment.errors[0]

    async def test_surviving_agents_still_contribute(self, market_data, rag_context,
                                                     conservative_profile):
        orchestrator = Orchestrator(
            agents=[TechnicalAgent(), FundamentalAgent(), ExplodingAgent()]
        )
        result = await orchestrator.run(
            "RELIANCE", market_data, rag_context, conservative_profile
        )
        survivors = [o for o in result.agent_outputs if o.status == AgentStatus.SUCCESS]
        assert len(survivors) == 2
        assert result.sources, "fundamental citations must survive the sentiment failure"

    async def test_missing_agent_caps_confidence(self, market_data, rag_context,
                                                 conservative_profile):
        full = await Orchestrator().run(
            "RELIANCE", market_data, rag_context, conservative_profile
        )
        degraded = await Orchestrator(
            agents=[TechnicalAgent(), FundamentalAgent(), ExplodingAgent()]
        ).run("RELIANCE", market_data, rag_context, conservative_profile)

        assert degraded.confidence < full.confidence
        assert degraded.confidence <= 0.65
        assert degraded.data_quality != DataQuality.HIGH

    async def test_failure_is_explained_in_reasoning_and_trace(self, market_data, rag_context,
                                                               conservative_profile):
        result = await Orchestrator(
            agents=[TechnicalAgent(), FundamentalAgent(), ExplodingAgent()]
        ).run("RELIANCE", market_data, rag_context, conservative_profile)

        assert any("degraded coverage" in r.lower() for r in result.reasoning)
        trace_text = " ".join(t.summary for t in result.reasoning_trace)
        assert "FAILED" in trace_text


class TestScenarioB_NoRagEvidence:
    async def test_empty_retrieval_returns_insufficient_data(self, rag_context_empty):
        out = await FundamentalAgent().run("RELIANCE", {"rag_context": rag_context_empty})

        assert out.status == AgentStatus.INSUFFICIENT_DATA
        assert out.evidence == [], "must not invent citations"
        assert out.confidence == 0.0
        assert out.data_quality == DataQuality.NONE
        assert "no relevant filings" in " ".join(out.reasoning).lower()

    async def test_pipeline_produces_uncited_free_result(self, market_data, rag_context_empty,
                                                         conservative_profile):
        result = await Orchestrator().run(
            "RELIANCE", market_data, rag_context_empty, conservative_profile
        )

        assert "fundamental" in result.failed_agents
        # Any source that IS present must come from sentiment headlines, never
        # from fabricated filings.
        for source in result.sources:
            assert source.text
            assert source.source
        assert result.confidence <= 0.65

    async def test_irrelevant_chunks_do_not_become_a_signal(self, rag_fixtures):
        out = await FundamentalAgent().run(
            "RELIANCE", {"rag_context": rag_fixtures["RELIANCE_IRRELEVANT"]}
        )
        assert out.status == AgentStatus.INSUFFICIENT_DATA
        assert "neutral" in " ".join(out.reasoning).lower()


class TestScenarioC_IncompleteMarketData:
    async def test_partial_indicators_lower_quality_not_crash(self, market_data_degraded):
        out = await TechnicalAgent().run("RELIANCE", {"market_data": market_data_degraded})

        assert out.status == AgentStatus.SUCCESS
        assert out.data_quality in (DataQuality.LOW, DataQuality.MEDIUM)
        assert out.confidence < 0.7

    async def test_full_pipeline_on_degraded_feed(self, market_data_degraded, rag_context,
                                                  conservative_profile):
        result = await Orchestrator().run(
            "RELIANCE", market_data_degraded, rag_context, conservative_profile
        )

        assert result.final_signal in set(FinalSignal)
        assert result.data_quality in (DataQuality.MEDIUM, DataQuality.LOW)
        assert any("feed_gap" in f or "low-quality" in f.lower() for f in result.risk_factors)

    async def test_everything_missing_still_returns_a_result(self, conservative_profile):
        result = await Orchestrator().run("RELIANCE", {}, {"chunks": []}, conservative_profile)

        assert result.final_signal == FinalSignal.NEUTRAL
        assert result.confidence == 0.0
        assert result.recommendation.value == "HOLD"
        assert len(result.failed_agents) == 3
        assert result.sources == []
        assert len(result.reasoning_trace) == 8

    async def test_none_inputs_do_not_crash(self):
        result = await Orchestrator().run("RELIANCE", None, None, None)
        assert result.symbol == "RELIANCE"
        assert result.confidence == 0.0

    async def test_provider_exception_is_contained(self, conservative_profile):
        class BrokenMarketProvider:
            async def get_signals(self, symbol: str):
                raise TimeoutError("signal engine down")

        result = await Orchestrator(market_provider=BrokenMarketProvider()).run(
            "RELIANCE", None, {"chunks": []}, conservative_profile
        )
        assert result.confidence == 0.0
        assert any("market" in r.lower() for r in result.reasoning)
