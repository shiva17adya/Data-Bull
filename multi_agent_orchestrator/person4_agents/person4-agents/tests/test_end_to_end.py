"""Test 11: full mocked end-to-end run, output contract, and reasoning trace."""

from __future__ import annotations

import json

from app.adapters import (
    EmptyRAGProvider,
    MockMarketSignalProvider,
    MockProfileProvider,
    MockRAGProvider,
)
from app.api import analyze, analyze_sync
from app.orchestration.orchestrator import Orchestrator
from app.schemas.models import AnalysisResult, DataQuality, FinalSignal, Recommendation

EXPECTED_TRACE = [
    "input_received",
    "agents_started",
    "technical_result",
    "fundamental_result",
    "sentiment_result",
    "conflict_resolution",
    "risk_adjustment",
    "final_synthesis",
]


class TestEndToEnd:
    async def test_happy_path(self, market_data, rag_context, aggressive_profile):
        result = await analyze("RELIANCE", market_data, rag_context, aggressive_profile)

        assert isinstance(result, AnalysisResult)
        assert result.symbol == "RELIANCE"
        assert result.final_signal in set(FinalSignal)
        assert 0.0 <= result.confidence <= 1.0
        assert result.recommendation in set(Recommendation)
        assert result.data_quality == DataQuality.HIGH
        assert result.failed_agents == []
        assert len(result.agent_outputs) == 3
        assert result.sources
        assert result.reasoning
        assert result.total_latency_ms >= 0

    async def test_output_is_json_serializable_for_the_frontend(self, market_data, rag_context,
                                                                conservative_profile):
        result = await analyze("RELIANCE", market_data, rag_context, conservative_profile)
        payload = result.to_frontend_dict()

        encoded = json.dumps(payload)  # must not raise
        assert len(encoded) > 0

        required = {
            "final_signal", "confidence", "recommendation", "reasoning",
            "agent_outputs", "sources", "risk_factors", "personalization",
            "data_quality", "failed_agents", "reasoning_trace",
        }
        assert required.issubset(payload.keys())
        assert isinstance(payload["final_signal"], str)
        assert isinstance(payload["agent_outputs"], list)

    async def test_agent_output_contract(self, market_data, rag_context, aggressive_profile):
        result = await analyze("RELIANCE", market_data, rag_context, aggressive_profile)
        for agent in result.agent_outputs:
            payload = agent.model_dump(mode="json")
            assert set(payload.keys()) >= {
                "agent", "status", "signal", "confidence", "reasoning",
                "evidence", "data_quality", "latency_ms", "errors",
            }
            assert payload["signal"] in {"BULLISH", "NEUTRAL", "BEARISH"}
            assert payload["status"] in {"success", "insufficient_data", "failed"}

    async def test_every_source_is_traceable(self, market_data, rag_context, aggressive_profile):
        result = await analyze("RELIANCE", market_data, rag_context, aggressive_profile)
        supplied = {c["source"] for c in rag_context["chunks"]}
        supplied |= {n["source"] for n in market_data["sentiment"]["news"]}
        for source in result.sources:
            assert source.source in supplied, f"unrecognised citation: {source.source}"

    def test_sync_wrapper(self, market_data, rag_context, aggressive_profile):
        result = analyze_sync("RELIANCE", market_data, rag_context, aggressive_profile)
        assert isinstance(result, AnalysisResult)


class TestReasoningTrace:
    async def test_trace_has_all_eight_stages_in_order(self, market_data, rag_context,
                                                       conservative_profile):
        result = await analyze("RELIANCE", market_data, rag_context, conservative_profile)
        stages = [t.stage for t in result.reasoning_trace]
        assert stages == EXPECTED_TRACE

    async def test_trace_steps_are_numbered_sequentially(self, market_data, rag_context,
                                                         conservative_profile):
        result = await analyze("RELIANCE", market_data, rag_context, conservative_profile)
        assert [t.step for t in result.reasoning_trace] == list(range(1, 9))

    async def test_trace_is_renderable_without_internals(self, market_data, rag_context,
                                                         conservative_profile):
        """Frontend only needs step / stage / summary."""
        result = await analyze("RELIANCE", market_data, rag_context, conservative_profile)
        for event in result.reasoning_trace:
            assert isinstance(event.summary, str) and event.summary.strip()
            assert isinstance(event.stage, str) and event.stage.strip()
            assert isinstance(event.timestamp, str)
            json.dumps(event.model_dump(mode="json"))

    async def test_trace_survives_failures(self, market_data, conservative_profile):
        result = await analyze("RELIANCE", market_data, {"chunks": []}, conservative_profile)
        stages = [t.stage for t in result.reasoning_trace]
        assert stages == EXPECTED_TRACE


class TestProviderPath:
    """Person 5 can pass adapters instead of raw payloads."""

    async def test_runs_from_providers(self):
        orchestrator = Orchestrator(
            market_provider=MockMarketSignalProvider(),
            rag_provider=MockRAGProvider(),
            profile_provider=MockProfileProvider(),
        )
        result = await orchestrator.run("RELIANCE")
        assert result.confidence > 0
        assert result.sources

    async def test_analyze_accepts_providers(self, conservative_profile):
        result = await analyze(
            "RELIANCE",
            market_provider=MockMarketSignalProvider(),
            rag_provider=EmptyRAGProvider(),
            user_profile=conservative_profile,
        )
        assert "fundamental" in result.failed_agents
        assert result.confidence <= 0.65
