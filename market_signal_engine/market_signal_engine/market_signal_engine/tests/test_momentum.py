"""Tests for the price momentum signal."""

from __future__ import annotations

import pytest

from app.config import MOMENTUM_LOOKBACK, SIGNAL_MOMENTUM
from app.models.schemas import SignalLabel
from app.signals.momentum import calculate_momentum, required_candles
from tests.conftest import flat_series, make_candles


def test_strong_positive_momentum_is_bullish():
    # 100 -> 110 over 5 periods = +10%
    result = calculate_momentum(make_candles([100.0, 102.0, 104.0, 106.0, 108.0, 110.0]))
    assert result.signal is SignalLabel.BULLISH
    assert result.value == pytest.approx(10.0, abs=0.01)
    assert result.name == SIGNAL_MOMENTUM


def test_strong_negative_momentum_is_bearish():
    result = calculate_momentum(make_candles([100.0, 98.0, 96.0, 94.0, 92.0, 90.0]))
    assert result.signal is SignalLabel.BEARISH
    assert result.value == pytest.approx(-10.0, abs=0.01)


def test_flat_price_is_neutral_with_maximum_confidence():
    result = calculate_momentum(flat_series(100.0, 10))
    assert result.signal is SignalLabel.NEUTRAL
    assert result.value == 0.0
    assert result.confidence == 1.0


def test_small_move_stays_neutral():
    # +1% is inside the +/-2% band
    result = calculate_momentum(make_candles([100.0, 100.2, 100.4, 100.6, 100.8, 101.0]))
    assert result.signal is SignalLabel.NEUTRAL


def test_exactly_at_bullish_threshold_is_bullish():
    result = calculate_momentum(make_candles([100.0, 100.0, 100.0, 100.0, 100.0, 102.0]))
    assert result.signal is SignalLabel.BULLISH
    assert result.value == pytest.approx(2.0, abs=0.001)
    # Sitting exactly on the boundary means minimum directional confidence.
    assert result.confidence == 0.5


def test_exactly_at_bearish_threshold_is_bearish():
    result = calculate_momentum(make_candles([100.0, 100.0, 100.0, 100.0, 100.0, 98.0]))
    assert result.signal is SignalLabel.BEARISH
    assert result.confidence == 0.5


def test_confidence_increases_with_stronger_move():
    weak = calculate_momentum(make_candles([100.0, 100.0, 100.0, 100.0, 100.0, 103.0]))
    strong = calculate_momentum(make_candles([100.0, 100.0, 100.0, 100.0, 100.0, 130.0]))
    assert strong.confidence > weak.confidence
    assert strong.confidence == 1.0


def test_insufficient_data_is_unavailable():
    result = calculate_momentum(make_candles([100.0, 101.0]))
    assert result.signal is SignalLabel.UNAVAILABLE
    assert result.confidence == 0.0
    assert result.value is None
    assert "Insufficient historical data" in result.evidence[0]


def test_empty_series_is_unavailable():
    result = calculate_momentum([])
    assert result.signal is SignalLabel.UNAVAILABLE


def test_single_candle_is_unavailable():
    result = calculate_momentum(make_candles([100.0]))
    assert result.signal is SignalLabel.UNAVAILABLE


def test_invalid_lookback_is_unavailable():
    result = calculate_momentum(flat_series(100.0, 30), lookback=0)
    assert result.signal is SignalLabel.UNAVAILABLE


def test_custom_lookback_changes_reference_point():
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0]
    short = calculate_momentum(make_candles(closes), lookback=1)
    long = calculate_momentum(make_candles(closes), lookback=10)
    assert short.value == pytest.approx(0.92, abs=0.01)
    assert long.value == pytest.approx(10.0, abs=0.01)


def test_required_candles_is_lookback_plus_one():
    assert required_candles(MOMENTUM_LOOKBACK) == MOMENTUM_LOOKBACK + 1


def test_evidence_is_populated_with_numbers():
    result = calculate_momentum(make_candles([100.0, 102.0, 104.0, 106.0, 108.0, 110.0]))
    assert any("10.00%" in line for line in result.evidence)


def test_deterministic_across_repeated_calls():
    candles = make_candles([100.0, 102.0, 104.0, 106.0, 108.0, 110.0])
    first = calculate_momentum(candles)
    second = calculate_momentum(candles)
    assert first.model_dump() == second.model_dump()
