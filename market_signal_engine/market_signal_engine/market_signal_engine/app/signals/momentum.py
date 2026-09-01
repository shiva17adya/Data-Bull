"""Signal 1 -- price momentum.

    momentum_percent = ((current_close - lookback_close) / lookback_close) * 100

Classified against a symmetric threshold pair. This is a transparent trend
proxy, not a forecast.
"""

from __future__ import annotations

from typing import Sequence

from app.config import (
    MOMENTUM_BEARISH_THRESHOLD,
    MOMENTUM_BULLISH_THRESHOLD,
    MOMENTUM_FULL_SCALE,
    MOMENTUM_LOOKBACK,
    MOMENTUM_NEUTRAL_SCALE,
    SIGNAL_MOMENTUM,
)
from app.models.schemas import MarketCandle, SignalLabel, SignalResult
from app.signals.common import round_confidence, round_value, scaled_confidence, unavailable


def required_candles(lookback: int = MOMENTUM_LOOKBACK) -> int:
    """Number of candles needed: the lookback bar plus the current bar."""
    return lookback + 1


def calculate_momentum(
    candles: Sequence[MarketCandle],
    lookback: int = MOMENTUM_LOOKBACK,
) -> SignalResult:
    """Classify price momentum over ``lookback`` periods."""
    if lookback < 1:
        return unavailable(SIGNAL_MOMENTUM, "Momentum lookback must be at least 1 period.")

    needed = required_candles(lookback)
    if len(candles) < needed:
        return unavailable(
            SIGNAL_MOMENTUM,
            f"Insufficient historical data for momentum: {len(candles)} candles "
            f"available, {needed} required.",
        )

    current_close = candles[-1].close
    past_close = candles[-needed].close

    if past_close <= 0:
        return unavailable(
            SIGNAL_MOMENTUM, "Reference close price is not positive; momentum is undefined."
        )

    momentum_percent = ((current_close - past_close) / past_close) * 100.0

    signal, confidence = _classify(momentum_percent)
    direction = "increased" if momentum_percent >= 0 else "decreased"

    evidence = [
        f"Price {direction} {abs(momentum_percent):.2f}% over the {lookback}-period lookback "
        f"({past_close:.2f} -> {current_close:.2f}).",
        f"Classification thresholds: BULLISH >= {MOMENTUM_BULLISH_THRESHOLD:.1f}%, "
        f"BEARISH <= {MOMENTUM_BEARISH_THRESHOLD:.1f}%.",
    ]

    return SignalResult(
        name=SIGNAL_MOMENTUM,
        signal=signal,
        value=round_value(momentum_percent),
        confidence=round_confidence(confidence),
        evidence=evidence,
    )


def _classify(momentum_percent: float) -> tuple[SignalLabel, float]:
    """Return the label and its confidence for a momentum percentage."""
    if momentum_percent >= MOMENTUM_BULLISH_THRESHOLD:
        excess = momentum_percent - MOMENTUM_BULLISH_THRESHOLD
        return SignalLabel.BULLISH, scaled_confidence(excess, MOMENTUM_FULL_SCALE)

    if momentum_percent <= MOMENTUM_BEARISH_THRESHOLD:
        excess = MOMENTUM_BEARISH_THRESHOLD - momentum_percent
        return SignalLabel.BEARISH, scaled_confidence(excess, MOMENTUM_FULL_SCALE)

    # Neutral: the closer to a flat 0%, the more confident the neutral call.
    distance_from_boundary = MOMENTUM_NEUTRAL_SCALE - abs(momentum_percent)
    return SignalLabel.NEUTRAL, scaled_confidence(distance_from_boundary, MOMENTUM_NEUTRAL_SCALE)
