"""Tests for the volume anomaly signal."""

from __future__ import annotations

import pytest

from app.config import SIGNAL_VOLUME, VOLUME_LOOKBACK
from app.models.schemas import SignalLabel
from app.signals.volume import calculate_volume_anomaly, required_candles
from tests.conftest import make_candles

BASE_VOLUME = 1_000_000.0


def _series(final_close: float, final_volume, previous_close: float = 100.0, length: int = 21):
    """Build a series with a flat history and a controlled final candle."""
    closes = [previous_close] * (length - 1) + [final_close]
    volumes = [BASE_VOLUME] * (length - 1) + [final_volume]
    return make_candles(closes, volumes)


def test_high_volume_with_rising_price_is_bullish():
    result = calculate_volume_anomaly(_series(105.0, BASE_VOLUME * 2.0))
    assert result.signal is SignalLabel.BULLISH
    assert result.value == pytest.approx(2.0, abs=0.01)
    assert result.name == SIGNAL_VOLUME


def test_high_volume_with_falling_price_is_bearish():
    result = calculate_volume_anomaly(_series(95.0, BASE_VOLUME * 2.0))
    assert result.signal is SignalLabel.BEARISH
    assert result.value == pytest.approx(2.0, abs=0.01)


def test_high_volume_with_flat_price_is_neutral():
    result = calculate_volume_anomaly(_series(100.0, BASE_VOLUME * 2.0))
    assert result.signal is SignalLabel.NEUTRAL
    assert "directionless" in " ".join(result.evidence)


def test_low_volume_is_neutral():
    result = calculate_volume_anomaly(_series(105.0, BASE_VOLUME * 0.4))
    assert result.signal is SignalLabel.NEUTRAL
    assert result.value == pytest.approx(0.4, abs=0.01)


def test_normal_volume_is_neutral():
    result = calculate_volume_anomaly(_series(105.0, BASE_VOLUME))
    assert result.signal is SignalLabel.NEUTRAL
    assert result.value == pytest.approx(1.0, abs=0.01)


def test_missing_current_volume_is_unavailable():
    result = calculate_volume_anomaly(_series(105.0, None))
    assert result.signal is SignalLabel.UNAVAILABLE
    assert result.confidence == 0.0
    assert "Volume data unavailable" in result.evidence[0]


def test_missing_historical_volume_is_unavailable():
    candles = make_candles(
        [100.0] * 20 + [105.0],
        [None] * 20 + [BASE_VOLUME],
    )
    result = calculate_volume_anomaly(candles)
    assert result.signal is SignalLabel.UNAVAILABLE
    assert "historical periods" in result.evidence[0]


def test_zero_average_volume_is_unavailable():
    candles = make_candles([100.0] * 20 + [105.0], [0.0] * 20 + [BASE_VOLUME])
    result = calculate_volume_anomaly(candles)
    assert result.signal is SignalLabel.UNAVAILABLE
    assert "undefined" in result.evidence[0]


def test_zero_current_volume_is_handled_without_crashing():
    result = calculate_volume_anomaly(_series(105.0, 0.0))
    assert result.signal is SignalLabel.NEUTRAL
    assert result.value == 0.0


def test_insufficient_history_is_unavailable():
    result = calculate_volume_anomaly(make_candles([100.0] * 5, [BASE_VOLUME] * 5))
    assert result.signal is SignalLabel.UNAVAILABLE
    assert "Insufficient historical data" in result.evidence[0]


def test_empty_series_is_unavailable():
    assert calculate_volume_anomaly([]).signal is SignalLabel.UNAVAILABLE


def test_invalid_lookback_is_unavailable():
    result = calculate_volume_anomaly(_series(105.0, BASE_VOLUME), lookback=0)
    assert result.signal is SignalLabel.UNAVAILABLE


def test_extreme_volume_reaches_full_confidence():
    result = calculate_volume_anomaly(_series(105.0, BASE_VOLUME * 50))
    assert result.signal is SignalLabel.BULLISH
    assert result.confidence == 1.0


def test_confidence_grows_with_volume_ratio():
    mild = calculate_volume_anomaly(_series(105.0, BASE_VOLUME * 1.6))
    heavy = calculate_volume_anomaly(_series(105.0, BASE_VOLUME * 2.5))
    assert heavy.confidence > mild.confidence


def test_required_candles_is_lookback_plus_one():
    assert required_candles(VOLUME_LOOKBACK) == VOLUME_LOOKBACK + 1


def test_deterministic_across_repeated_calls():
    candles = _series(105.0, BASE_VOLUME * 2.0)
    assert calculate_volume_anomaly(candles).model_dump() == (
        calculate_volume_anomaly(candles).model_dump()
    )
