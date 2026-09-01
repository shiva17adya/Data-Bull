"""Degraded-data behaviour: the module must bend, never break."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.data.mock_data import (
    DEMO_CORRUPT,
    DEMO_NO_VOLUME,
    DEMO_SHORT_HISTORY,
    MockMarketDataProvider,
)
from app.data.provider import SymbolNotFoundError
from app.models.schemas import DataStatus, MarketCandle, SignalLabel, build_candles
from app.signals.engine import SignalEngine
from tests.conftest import BASE_TIME

VALID_BAR = {
    "timestamp": BASE_TIME,
    "open": 100.0,
    "high": 105.0,
    "low": 95.0,
    "close": 102.0,
    "volume": 1_000_000.0,
}


def _bar(**overrides):
    bar = dict(VALID_BAR)
    bar.update(overrides)
    return bar


@pytest.fixture
def engine() -> SignalEngine:
    return SignalEngine(MockMarketDataProvider())


# ----------------------------------------------------------------------
# Candle-level validation
# ----------------------------------------------------------------------
def test_valid_bar_is_accepted():
    candles, warnings = build_candles([VALID_BAR])
    assert len(candles) == 1
    assert warnings == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"high": 90.0, "low": 95.0},        # high below low
        {"high": 101.0},                     # high below close
        {"low": 103.0},                      # low above close
        {"close": 0.0},                      # zero price
        {"close": -5.0},                     # negative price
        {"open": -1.0},                      # negative price
        {"volume": -100.0},                  # negative volume
        {"close": float("nan")},             # NaN
        {"close": float("inf")},             # infinity
        {"open": None},                      # missing required field
        {"close": "not-a-number"},           # wrong type
    ],
    ids=[
        "high_below_low",
        "high_below_close",
        "low_above_close",
        "zero_price",
        "negative_close",
        "negative_open",
        "negative_volume",
        "nan_close",
        "inf_close",
        "none_open",
        "string_close",
    ],
)
def test_invalid_bars_are_discarded_with_a_warning(overrides):
    candles, warnings = build_candles([_bar(**overrides)])
    assert candles == []
    assert len(warnings) == 1
    assert "invalid values" in warnings[0]


def test_zero_volume_is_valid_data_not_an_error():
    candles, warnings = build_candles([_bar(volume=0.0)])
    assert len(candles) == 1
    assert warnings == []


def test_null_volume_is_valid_and_preserved():
    candles, warnings = build_candles([_bar(volume=None)])
    assert len(candles) == 1
    assert candles[0].volume is None
    assert warnings == []


def test_mixed_batch_keeps_good_bars_and_reports_bad_ones():
    candles, warnings = build_candles([VALID_BAR, _bar(high=1.0), VALID_BAR])
    assert len(candles) == 2
    assert len(warnings) == 1
    assert "index 1" in warnings[0]


def test_direct_model_construction_still_raises():
    """Validation is real, not just a filter in build_candles."""
    with pytest.raises(ValidationError):
        MarketCandle(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            open=100.0,
            high=90.0,
            low=95.0,
            close=100.0,
            volume=1.0,
        )


def test_empty_input_produces_no_candles_and_no_warnings():
    candles, warnings = build_candles([])
    assert candles == []
    assert warnings == []


# ----------------------------------------------------------------------
# Case 1 -- missing volume
# ----------------------------------------------------------------------
def test_demo_no_volume_degrades_gracefully(engine):
    response = engine.analyze(DEMO_NO_VOLUME)
    assert response.data_status is DataStatus.DEGRADED
    assert response.signals["volume_anomaly"].signal is SignalLabel.UNAVAILABLE
    assert response.signals["price_momentum"].signal is not SignalLabel.UNAVAILABLE
    assert response.signals["rsi"].signal is not SignalLabel.UNAVAILABLE
    assert any("Volume data unavailable" in w for w in response.warnings)
    assert 0.0 <= response.confidence <= 1.0


# ----------------------------------------------------------------------
# Case 2 -- insufficient history
# ----------------------------------------------------------------------
def test_demo_short_history_reports_which_signals_failed(engine):
    response = engine.analyze(DEMO_SHORT_HISTORY)
    assert response.signals["price_momentum"].signal is not SignalLabel.UNAVAILABLE
    assert response.signals["volume_anomaly"].signal is SignalLabel.UNAVAILABLE
    assert response.signals["rsi"].signal is SignalLabel.UNAVAILABLE
    assert response.data_status is DataStatus.DEGRADED
    assert any("Insufficient historical data" in w for w in response.warnings)


# ----------------------------------------------------------------------
# Case 3 -- invalid OHLC values
# ----------------------------------------------------------------------
def test_demo_corrupt_discards_bad_bars_but_still_responds(engine):
    market_data = MockMarketDataProvider().get_market_data(DEMO_CORRUPT)
    assert market_data.warnings, "corrupt fixture should report discarded candles"

    response = engine.analyze(DEMO_CORRUPT)
    assert response.data_status is DataStatus.DEGRADED
    assert response.overall_signal is not SignalLabel.UNAVAILABLE
    assert 0.0 <= response.confidence <= 1.0
    assert any("discarded" in w for w in response.warnings)


# ----------------------------------------------------------------------
# Case 4 -- unknown symbol
# ----------------------------------------------------------------------
def test_unknown_symbol_raises_symbol_not_found(engine):
    with pytest.raises(SymbolNotFoundError):
        engine.analyze("RELIANCE_X")


def test_symbol_lookup_is_case_and_whitespace_insensitive(engine):
    response = engine.analyze("  reliance  ")
    assert response.symbol == "RELIANCE"


def test_zero_limit_returns_no_candles_without_crashing():
    data = MockMarketDataProvider().get_market_data("RELIANCE", limit=0)
    assert data.candles == []


def test_engine_handles_zero_limit_provider_data(engine):
    data = MockMarketDataProvider().get_market_data("RELIANCE", limit=0)
    response = engine.analyze_market_data(data)
    assert response.data_status is DataStatus.UNAVAILABLE
    assert response.confidence == 0.0


def test_single_candle_from_provider_does_not_crash(engine):
    data = MockMarketDataProvider().get_market_data("RELIANCE", limit=1)
    response = engine.analyze_market_data(data)
    assert response.data_status is DataStatus.UNAVAILABLE
    assert response.market_data is not None
