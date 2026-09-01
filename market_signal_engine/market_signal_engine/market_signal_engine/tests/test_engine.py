"""Tests for the combined signal engine."""

from __future__ import annotations

import pytest

from app.config import SIGNAL_MOMENTUM, SIGNAL_RSI, SIGNAL_VOLUME
from app.data.mock_data import MockMarketDataProvider
from app.models.schemas import DataStatus, MarketData, SignalLabel
from app.signals.engine import SignalEngine
from tests.conftest import flat_series, make_candles, market_data

ALL_SIGNALS = (SIGNAL_MOMENTUM, SIGNAL_VOLUME, SIGNAL_RSI)


@pytest.fixture
def engine() -> SignalEngine:
    return SignalEngine(MockMarketDataProvider())


def _rising(count: int = 40, step: float = 0.02):
    closes = [100.0]
    for _ in range(count - 1):
        closes.append(round(closes[-1] * (1 + step), 4))
    return closes


def _falling(count: int = 40, step: float = 0.02):
    closes = [100.0]
    for _ in range(count - 1):
        closes.append(round(closes[-1] * (1 - step), 4))
    return closes


def test_all_three_dimensions_are_always_present(engine):
    response = engine.analyze("RELIANCE")
    assert set(response.signals) == set(ALL_SIGNALS)
    for name in ALL_SIGNALS:
        result = response.signals[name]
        assert result.name == name
        assert 0.0 <= result.confidence <= 1.0
        assert result.evidence


def test_strong_uptrend_with_volume_spike_is_bullish(engine):
    closes = _rising()
    volumes = [1_000_000.0] * 39 + [3_000_000.0]
    response = engine.analyze_market_data(market_data(make_candles(closes, volumes)))
    assert response.signals[SIGNAL_MOMENTUM].signal is SignalLabel.BULLISH
    assert response.signals[SIGNAL_VOLUME].signal is SignalLabel.BULLISH
    # RSI is pinned at 100 on an uninterrupted uptrend, which reads BEARISH.
    assert response.signals[SIGNAL_RSI].signal is SignalLabel.BEARISH
    # Momentum (0.40) + volume (0.30) outweigh RSI (0.30): score = +0.40
    assert response.overall_signal is SignalLabel.BULLISH


def test_strong_downtrend_with_volume_spike_is_bearish(engine):
    closes = _falling()
    volumes = [1_000_000.0] * 39 + [3_000_000.0]
    response = engine.analyze_market_data(market_data(make_candles(closes, volumes)))
    assert response.signals[SIGNAL_MOMENTUM].signal is SignalLabel.BEARISH
    assert response.signals[SIGNAL_VOLUME].signal is SignalLabel.BEARISH
    assert response.overall_signal is SignalLabel.BEARISH


def test_flat_market_is_neutral(engine):
    response = engine.analyze_market_data(market_data(flat_series(100.0, 40)))
    assert response.overall_signal is SignalLabel.NEUTRAL
    assert response.data_status is DataStatus.OK


def test_conflicting_signals_reduce_confidence(engine):
    """Same momentum, but one case has agreement and the other conflict."""
    aligned = engine.analyze_market_data(
        market_data(make_candles(_rising(), [1_000_000.0] * 39 + [3_000_000.0]))
    )
    conflicted = engine.analyze_market_data(
        market_data(make_candles(_rising(), [1_000_000.0] * 39 + [200_000.0]))
    )
    assert aligned.confidence > conflicted.confidence
    assert any("do not fully agree" in line for line in conflicted.reasoning)


def test_missing_volume_dimension_still_produces_a_response(engine):
    candles = make_candles(_rising(), [None] * 40)
    response = engine.analyze_market_data(market_data(candles))
    assert response.signals[SIGNAL_VOLUME].signal is SignalLabel.UNAVAILABLE
    assert response.signals[SIGNAL_MOMENTUM].signal is SignalLabel.BULLISH
    assert response.data_status is DataStatus.DEGRADED
    assert response.overall_signal in {
        SignalLabel.BULLISH,
        SignalLabel.NEUTRAL,
        SignalLabel.BEARISH,
    }
    assert response.warnings


def test_missing_dimension_lowers_confidence_versus_complete_data(engine):
    complete = engine.analyze_market_data(
        market_data(make_candles(_rising(), [1_000_000.0] * 40))
    )
    partial = engine.analyze_market_data(market_data(make_candles(_rising(), [None] * 40)))
    assert partial.confidence < complete.confidence


def test_no_candles_returns_unavailable_status(engine):
    response = engine.analyze_market_data(MarketData(symbol="EMPTY", candles=[]))
    assert response.data_status is DataStatus.UNAVAILABLE
    assert response.overall_signal is SignalLabel.NEUTRAL
    assert response.confidence == 0.0
    assert response.market_data is None
    assert response.signals == {}


def test_too_few_candles_returns_all_dimensions_unavailable(engine):
    response = engine.analyze_market_data(market_data(make_candles([100.0, 101.0])))
    assert response.data_status is DataStatus.UNAVAILABLE
    assert all(r.signal is SignalLabel.UNAVAILABLE for r in response.signals.values())
    assert response.confidence == 0.0


def test_provider_warnings_propagate_and_degrade_status(engine):
    data = market_data(
        make_candles(_rising(), [1_000_000.0] * 40),
        warnings=["Candle at index 3 contains invalid values and was discarded."],
    )
    response = engine.analyze_market_data(data)
    assert response.data_status is DataStatus.DEGRADED
    assert "Candle at index 3 contains invalid values and was discarded." in response.warnings


def test_data_warnings_reduce_confidence(engine):
    candles = make_candles(_rising(), [1_000_000.0] * 40)
    clean = engine.analyze_market_data(market_data(candles))
    dirty = engine.analyze_market_data(market_data(candles, warnings=["a problem"]))
    assert dirty.confidence < clean.confidence


@pytest.mark.parametrize("symbol", ["RELIANCE", "TCS", "INFY", "HDFCBANK"])
def test_confidence_within_bounds_for_every_symbol(engine, symbol):
    response = engine.analyze(symbol)
    assert 0.0 <= response.confidence <= 1.0
    for result in response.signals.values():
        assert 0.0 <= result.confidence <= 1.0


@pytest.mark.parametrize("symbol", ["RELIANCE", "TCS", "INFY", "HDFCBANK"])
def test_engine_is_deterministic(engine, symbol):
    first = engine.analyze(symbol)
    second = engine.analyze(symbol)
    assert first.overall_signal == second.overall_signal
    assert first.confidence == second.confidence
    assert first.signals == second.signals
    assert first.reasoning == second.reasoning


def test_fresh_provider_instance_gives_identical_results():
    """Determinism must survive process-level and instance-level boundaries."""
    first = SignalEngine(MockMarketDataProvider()).analyze("RELIANCE")
    second = SignalEngine(MockMarketDataProvider()).analyze("RELIANCE")
    assert first.signals == second.signals
    assert first.confidence == second.confidence


def test_overall_signal_is_never_unavailable(engine):
    response = engine.analyze_market_data(market_data(make_candles([100.0, 101.0])))
    assert response.overall_signal is not SignalLabel.UNAVAILABLE


def test_reasoning_mentions_every_dimension(engine):
    response = engine.analyze("RELIANCE")
    assert len(response.reasoning) >= 4


def test_lookback_override_changes_momentum(engine):
    short = engine.analyze("RELIANCE", lookback=1)
    long = engine.analyze("RELIANCE", lookback=30)
    assert short.signals[SIGNAL_MOMENTUM].value != long.signals[SIGNAL_MOMENTUM].value


def test_calculator_exception_is_contained(engine, monkeypatch):
    """A crashing calculator degrades one dimension, not the whole response."""

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("app.signals.engine.calculate_rsi", boom)
    response = engine.analyze_market_data(
        market_data(make_candles(_rising(), [1_000_000.0] * 40))
    )
    assert response.signals[SIGNAL_RSI].signal is SignalLabel.UNAVAILABLE
    assert response.signals[SIGNAL_MOMENTUM].signal is SignalLabel.BULLISH
    assert response.data_status is DataStatus.DEGRADED
