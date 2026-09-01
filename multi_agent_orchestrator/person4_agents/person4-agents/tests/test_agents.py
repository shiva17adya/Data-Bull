"""Tests 1-3: Technical, Fundamental and Sentiment agents."""

from __future__ import annotations

import pytest

from app.agents import FundamentalAgent, SentimentAgent, TechnicalAgent
from app.schemas.models import AgentStatus, DataQuality, Signal


# ---------------------------------------------------------------- technical


class TestTechnicalAgent:
    async def test_reads_bullish_indicators(self, market_data):
        out = await TechnicalAgent().run("RELIANCE", {"market_data": market_data})

        assert out.agent == "technical"
        assert out.status == AgentStatus.SUCCESS
        assert out.signal == Signal.BULLISH
        assert 0.0 < out.confidence <= 1.0
        assert out.data_quality == DataQuality.HIGH
        assert out.reasoning, "agent must explain itself"
        assert out.errors == []
        assert out.latency_ms >= 0

    async def test_reads_bearish_indicators(self):
        bearish = {
            "symbol": "RELIANCE",
            "price": 1180.0,
            "feed_status": "ok",
            "indicators": {
                "rsi_14": 38.2,
                "momentum_5d_pct": -4.1,
                "momentum_20d_pct": -9.4,
                "volume_ratio_20d": 1.7,
                "sma_20": 1240.0,
                "sma_50": 1305.0,
                "sma_200": 1288.0,
                "macd_histogram": -3.9,
                "volatility_30d_pct": 26.0,
            },
        }
        out = await TechnicalAgent().run("RELIANCE", {"market_data": bearish})
        assert out.signal == Signal.BEARISH
        assert out.status == AgentStatus.SUCCESS

    async def test_cites_actual_indicator_values(self, market_data):
        out = await TechnicalAgent().run("RELIANCE", {"market_data": market_data})
        joined = " ".join(out.reasoning)
        assert "RSI" in joined
        assert "61.4" in joined  # the value it was actually given

    async def test_no_indicators_is_insufficient_not_crash(self):
        out = await TechnicalAgent().run("RELIANCE", {"market_data": {}})
        assert out.status == AgentStatus.INSUFFICIENT_DATA
        assert out.signal == Signal.NEUTRAL
        assert out.data_quality == DataQuality.NONE

    async def test_malformed_indicators_are_ignored(self):
        payload = {
            "price": 1412.3,
            "indicators": {"rsi_14": "not-a-number", "momentum_20d_pct": None, "sma_50": 1341.0},
        }
        out = await TechnicalAgent().run("RELIANCE", {"market_data": payload})
        assert out.status in (AgentStatus.SUCCESS, AgentStatus.INSUFFICIENT_DATA)
        assert out.errors == []


# -------------------------------------------------------------- fundamental


class TestFundamentalAgent:
    async def test_grounds_claims_in_retrieved_evidence(self, rag_context):
        out = await FundamentalAgent().run("RELIANCE", {"rag_context": rag_context})

        assert out.status == AgentStatus.SUCCESS
        assert out.evidence, "fundamental agent must attach citations"
        supplied = {c["source"] for c in rag_context["chunks"]}
        for item in out.evidence:
            assert item.source in supplied, "no citation may be invented"
            assert item.text

    async def test_bullish_filings_produce_bullish_signal(self, rag_context):
        out = await FundamentalAgent().run("RELIANCE", {"rag_context": rag_context})
        assert out.signal == Signal.BULLISH

    async def test_bearish_filings_produce_bearish_signal(self, rag_context_bearish):
        out = await FundamentalAgent().run("RELIANCE", {"rag_context": rag_context_bearish})
        assert out.signal == Signal.BEARISH
        assert out.evidence

    async def test_reasoning_references_sources(self, rag_context):
        out = await FundamentalAgent().run("RELIANCE", {"rag_context": rag_context})
        joined = " ".join(out.reasoning)
        assert any(e.source in joined for e in out.evidence)

    async def test_chunk_without_attribution_is_dropped(self):
        rag = {"chunks": [{"text": "Revenue grew strongly this quarter."}]}  # no source
        out = await FundamentalAgent().run("RELIANCE", {"rag_context": rag})
        assert out.status == AgentStatus.INSUFFICIENT_DATA
        assert out.evidence == []


# ---------------------------------------------------------------- sentiment


class TestSentimentAgent:
    async def test_aggregates_headlines(self, market_data):
        out = await SentimentAgent().run("RELIANCE", {"market_data": market_data})

        assert out.status == AgentStatus.SUCCESS
        assert out.signal == Signal.BULLISH
        assert len(out.evidence) == len(market_data["sentiment"]["news"])
        assert out.data_quality == DataQuality.HIGH

    async def test_negative_coverage_is_surfaced(self, market_data):
        out = await SentimentAgent().run("RELIANCE", {"market_data": market_data})
        joined = " ".join(out.reasoning)
        assert "Countervailing" in joined, "opposing coverage must not be hidden"

    async def test_bearish_headlines_produce_bearish_signal(self):
        payload = {
            "sentiment": {
                "news": [
                    {"headline": "Reliance shares plunge after profit miss", "source": "Reuters",
                     "sentiment_score": -0.8},
                    {"headline": "Brokerages downgrade Reliance on weak margins", "source": "Mint",
                     "sentiment_score": -0.6},
                ]
            }
        }
        out = await SentimentAgent().run("RELIANCE", {"market_data": payload})
        assert out.signal == Signal.BEARISH

    async def test_lexicon_fallback_when_no_scores(self):
        payload = {
            "sentiment": {
                "news": [
                    {"headline": "Reliance profit surges to record high", "source": "ET"},
                    {"headline": "Jio wins spectrum approval", "source": "Mint"},
                ]
            }
        }
        out = await SentimentAgent().run("RELIANCE", {"market_data": payload})
        assert out.signal == Signal.BULLISH

    async def test_no_sentiment_data_is_insufficient(self):
        out = await SentimentAgent().run("RELIANCE", {"market_data": {"indicators": {}}})
        assert out.status == AgentStatus.INSUFFICIENT_DATA
        assert out.data_quality == DataQuality.NONE


# -------------------------------------------------------- contract guarantee


@pytest.mark.parametrize(
    "agent_cls", [TechnicalAgent, FundamentalAgent, SentimentAgent]
)
async def test_every_agent_returns_valid_contract_on_garbage(agent_cls):
    """Junk input must degrade, never raise."""
    out = await agent_cls().run("???", {"market_data": None, "rag_context": "not-a-dict"})
    assert out.agent == agent_cls.name
    assert out.status in set(AgentStatus)
    assert out.signal in set(Signal)
    assert 0.0 <= out.confidence <= 1.0
