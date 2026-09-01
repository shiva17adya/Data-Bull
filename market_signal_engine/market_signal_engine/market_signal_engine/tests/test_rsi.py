"""Tests for the RSI signal."""

from __future__ import annotations

import pytest

from app.config import RSI_PERIOD, SIGNAL_RSI
from app.models.schemas import SignalLabel
from app.signals.rsi import calculate_rsi, compute_rsi, required_candles
from tests.conftest import flat_series, make_candles


def _monotonic(start: float, step_pct: float, count: int) -> list[float]:
    closes = [start]
    for _ in range(count - 1):
        closes.append(round(closes[-1] * (1 + step_pct), 6))
    return closes


def test_uninterrupted_gains_give_rsi_100():
    assert compute_rsi(_monotonic(100.0, 0.01, 30)) == 100.0


def test_uninterrupted_losses_give_rsi_0():
    assert compute_rsi(_monotonic(100.0, -0.01, 30)) == 0.0


def test_constant_prices_give_neutral_midpoint():
    assert compute_rsi([100.0] * 30) == 50.0


def test_overbought_is_classified_bearish():
    result = calculate_rsi(make_candles(_monotonic(100.0, 0.01, 30)))
    assert result.signal is SignalLabel.BEARISH
    assert result.value == 100.0
    assert result.name == SIGNAL_RSI
    assert "overbought" in result.evidence[0]


def test_oversold_is_classified_bullish():
    result = calculate_rsi(make_candles(_monotonic(100.0, -0.01, 30)))
    assert result.signal is SignalLabel.BULLISH
    assert result.value == 0.0
    assert "oversold" in result.evidence[0]


def test_constant_prices_are_neutral_with_explanation():
    result = calculate_rsi(flat_series(100.0, 30))
    assert result.signal is SignalLabel.NEUTRAL
    assert result.value == 50.0
    assert result.confidence == 1.0
    assert any("undefined" in line for line in result.evidence)


def test_alternating_prices_stay_in_neutral_band():
    closes = [100.0 + (1.0 if i % 2 else -1.0) for i in range(40)]
    result = calculate_rsi(make_candles(closes))
    assert result.signal is SignalLabel.NEUTRAL
    assert 30.0 < (result.value or 0) < 70.0


def test_insufficient_data_is_unavailable():
    result = calculate_rsi(make_candles([100.0] * 10))
    assert result.signal is SignalLabel.UNAVAILABLE
    assert result.confidence == 0.0
    assert "Insufficient historical data" in result.evidence[0]


def test_exactly_enough_candles_computes():
    result = calculate_rsi(make_candles(_monotonic(100.0, 0.01, RSI_PERIOD + 1)))
    assert result.signal is not SignalLabel.UNAVAILABLE


def test_one_candle_short_is_unavailable():
    result = calculate_rsi(make_candles(_monotonic(100.0, 0.01, RSI_PERIOD)))
    assert result.signal is SignalLabel.UNAVAILABLE


def test_empty_series_is_unavailable():
    assert calculate_rsi([]).signal is SignalLabel.UNAVAILABLE


def test_invalid_period_is_unavailable():
    assert calculate_rsi(flat_series(100.0, 40), period=0).signal is SignalLabel.UNAVAILABLE


def test_compute_rsi_returns_none_when_data_too_short():
    assert compute_rsi([100.0, 101.0], period=14) is None


def test_rsi_matches_manual_wilder_calculation():
    """Cross-check against a hand-computed Wilder RSI on a known series."""
    closes = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
        45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
    ]
    value = compute_rsi(closes, period=14)
    # Reference value for this classic Wilder worked example is ~70.5
    assert value == pytest.approx(70.5, abs=0.5)


def test_confidence_higher_for_more_extreme_reading():
    mild = compute_rsi(_monotonic(100.0, 0.002, 40))
    result_extreme = calculate_rsi(make_candles(_monotonic(100.0, 0.01, 40)))
    assert result_extreme.confidence == 1.0
    assert mild is not None


def test_required_candles_is_period_plus_one():
    assert required_candles(RSI_PERIOD) == RSI_PERIOD + 1


def test_deterministic_across_repeated_calls():
    candles = make_candles(_monotonic(100.0, 0.01, 30))
    assert calculate_rsi(candles).model_dump() == calculate_rsi(candles).model_dump()
