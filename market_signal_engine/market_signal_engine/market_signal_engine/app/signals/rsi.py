"""Signal 3 -- Relative Strength Index (Wilder).

Standard Wilder implementation: the first average gain/loss is the simple mean
of the first ``period`` close-to-close changes, and every subsequent bar is
smoothed as

    avg = (previous_avg * (period - 1) + current) / period

then

    RS  = avg_gain / avg_loss
    RSI = 100 - (100 / (1 + RS))

Interpretation used here (RSI >= 70 overbought -> BEARISH pressure, RSI <= 30
oversold -> BULLISH pressure) is the conventional simplified reading. It is a
mean-reversion heuristic, not a guaranteed prediction of price direction.
"""

from __future__ import annotations

from typing import Optional, Sequence

from app.config import (
    RSI_CONSTANT_PRICE_VALUE,
    RSI_EXTREME_SCALE,
    RSI_NEUTRAL_SCALE,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    RSI_PERIOD,
    SIGNAL_RSI,
)
from app.models.schemas import MarketCandle, SignalLabel, SignalResult
from app.signals.common import round_confidence, round_value, scaled_confidence, unavailable


def required_candles(period: int = RSI_PERIOD) -> int:
    """``period`` price changes need ``period + 1`` closes."""
    return period + 1


def compute_rsi(closes: Sequence[float], period: int = RSI_PERIOD) -> Optional[float]:
    """Return the latest Wilder RSI, or None if it cannot be computed.

    Returns ``RSI_CONSTANT_PRICE_VALUE`` (50.0) when price never changes, since
    RSI is mathematically undefined with zero average gain and zero average loss.
    """
    if period < 1 or len(closes) < required_candles(period):
        return None

    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_gain == 0.0 and avg_loss == 0.0:
        return RSI_CONSTANT_PRICE_VALUE
    if avg_loss == 0.0:
        return 100.0
    if avg_gain == 0.0:
        return 0.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_rsi(
    candles: Sequence[MarketCandle],
    period: int = RSI_PERIOD,
) -> SignalResult:
    """Classify the latest RSI reading."""
    if period < 1:
        return unavailable(SIGNAL_RSI, "RSI period must be at least 1.")

    needed = required_candles(period)
    if len(candles) < needed:
        return unavailable(
            SIGNAL_RSI,
            f"Insufficient historical data for RSI: {len(candles)} candles available, "
            f"{needed} required for a {period}-period RSI.",
        )

    closes = [candle.close for candle in candles]
    rsi_value = compute_rsi(closes, period)

    if rsi_value is None:
        return unavailable(SIGNAL_RSI, "RSI could not be computed from the available closes.")

    signal, confidence = _classify(rsi_value)

    if rsi_value >= RSI_OVERBOUGHT:
        condition = "overbought conditions"
    elif rsi_value <= RSI_OVERSOLD:
        condition = "oversold conditions"
    else:
        condition = "neither overbought nor oversold conditions"

    evidence = [
        f"{period}-period RSI is {rsi_value:.2f}, indicating {condition}.",
        f"Classification thresholds: overbought >= {RSI_OVERBOUGHT:.0f}, "
        f"oversold <= {RSI_OVERSOLD:.0f}.",
    ]

    if rsi_value == RSI_CONSTANT_PRICE_VALUE and len(set(closes)) == 1:
        evidence.append(
            "Closing price was constant across the window; RSI is undefined and the "
            "neutral midpoint is reported."
        )

    return SignalResult(
        name=SIGNAL_RSI,
        signal=signal,
        value=round_value(rsi_value),
        confidence=round_confidence(confidence),
        evidence=evidence,
    )


def _classify(rsi_value: float) -> tuple[SignalLabel, float]:
    """Overbought reads bearish, oversold reads bullish, the middle is neutral."""
    if rsi_value >= RSI_OVERBOUGHT:
        excess = rsi_value - RSI_OVERBOUGHT
        return SignalLabel.BEARISH, scaled_confidence(excess, RSI_EXTREME_SCALE)

    if rsi_value <= RSI_OVERSOLD:
        excess = RSI_OVERSOLD - rsi_value
        return SignalLabel.BULLISH, scaled_confidence(excess, RSI_EXTREME_SCALE)

    distance_from_boundary = RSI_NEUTRAL_SCALE - abs(rsi_value - 50.0)
    return SignalLabel.NEUTRAL, scaled_confidence(distance_from_boundary, RSI_NEUTRAL_SCALE)
