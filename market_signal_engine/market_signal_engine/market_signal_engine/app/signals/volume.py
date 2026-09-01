"""Signal 2 -- volume anomaly.

    volume_ratio = current_volume / mean(previous VOLUME_LOOKBACK volumes)

Volume on its own carries no direction: heavy trading is only bullish if price
is also rising. The classification therefore combines the ratio with the most
recent price change:

    elevated volume + price up    -> BULLISH
    elevated volume + price down  -> BEARISH
    elevated volume + price flat  -> NEUTRAL
    low or normal volume          -> NEUTRAL
"""

from __future__ import annotations

from statistics import fmean
from typing import Sequence

from app.config import (
    SIGNAL_VOLUME,
    VOLUME_HIGH_FULL_SCALE,
    VOLUME_HIGH_RATIO,
    VOLUME_LOOKBACK,
    VOLUME_LOW_RATIO,
    VOLUME_NEUTRAL_SCALE,
    VOLUME_PRICE_LOOKBACK,
)
from app.models.schemas import MarketCandle, SignalLabel, SignalResult
from app.signals.common import round_confidence, round_value, scaled_confidence, unavailable


def required_candles(lookback: int = VOLUME_LOOKBACK) -> int:
    """The averaging window plus the current bar being compared against it."""
    return lookback + 1


def calculate_volume_anomaly(
    candles: Sequence[MarketCandle],
    lookback: int = VOLUME_LOOKBACK,
) -> SignalResult:
    """Classify current volume against its recent average, signed by price."""
    if lookback < 1:
        return unavailable(SIGNAL_VOLUME, "Volume lookback must be at least 1 period.")

    needed = required_candles(lookback)
    if len(candles) < needed:
        return unavailable(
            SIGNAL_VOLUME,
            f"Insufficient historical data for volume analysis: {len(candles)} candles "
            f"available, {needed} required.",
        )

    current_volume = candles[-1].volume
    if current_volume is None:
        return unavailable(SIGNAL_VOLUME, "Volume data unavailable for the current period.")

    history = [candle.volume for candle in candles[-needed:-1]]
    known_volumes = [volume for volume in history if volume is not None]

    if len(known_volumes) < lookback:
        missing = lookback - len(known_volumes)
        return unavailable(
            SIGNAL_VOLUME,
            f"Volume data unavailable for {missing} of the {lookback} historical periods "
            "required for the average.",
        )

    average_volume = fmean(known_volumes)
    if average_volume <= 0:
        return unavailable(
            SIGNAL_VOLUME,
            "Average historical volume is zero; the volume ratio is undefined.",
        )

    volume_ratio = current_volume / average_volume
    price_change = _price_change(candles)

    signal, confidence, descriptor = _classify(volume_ratio, price_change)

    deviation_percent = (volume_ratio - 1.0) * 100.0
    relation = "above" if deviation_percent >= 0 else "below"
    price_phrase = (
        "price momentum is positive"
        if price_change > 0
        else "price momentum is negative"
        if price_change < 0
        else "price is unchanged"
    )

    evidence = [
        f"Current volume is {abs(deviation_percent):.0f}% {relation} the {lookback}-period "
        f"average ({current_volume:,.0f} vs {average_volume:,.0f}).",
        f"Volume is {descriptor} while {price_phrase} over the last "
        f"{VOLUME_PRICE_LOOKBACK}-period window.",
    ]

    return SignalResult(
        name=SIGNAL_VOLUME,
        signal=signal,
        value=round_value(volume_ratio),
        confidence=round_confidence(confidence),
        evidence=evidence,
    )


def _price_change(candles: Sequence[MarketCandle]) -> float:
    """Close-to-close change over VOLUME_PRICE_LOOKBACK periods."""
    index = VOLUME_PRICE_LOOKBACK + 1
    if len(candles) < index:
        return 0.0
    return candles[-1].close - candles[-index].close


def _classify(volume_ratio: float, price_change: float) -> tuple[SignalLabel, float, str]:
    """Return label, confidence and a short descriptor of the volume regime."""
    if volume_ratio >= VOLUME_HIGH_RATIO:
        excess = volume_ratio - VOLUME_HIGH_RATIO
        confidence = scaled_confidence(excess, VOLUME_HIGH_FULL_SCALE)
        if price_change > 0:
            return SignalLabel.BULLISH, confidence, "elevated"
        if price_change < 0:
            return SignalLabel.BEARISH, confidence, "elevated"
        # Heavy volume with no price move gives conviction to neither side.
        return SignalLabel.NEUTRAL, confidence, "elevated but directionless"

    if volume_ratio <= VOLUME_LOW_RATIO:
        distance = VOLUME_LOW_RATIO - volume_ratio
        confidence = scaled_confidence(distance, VOLUME_NEUTRAL_SCALE)
        return SignalLabel.NEUTRAL, confidence, "subdued, indicating weak conviction"

    distance = min(VOLUME_HIGH_RATIO - volume_ratio, volume_ratio - VOLUME_LOW_RATIO)
    confidence = scaled_confidence(distance, VOLUME_NEUTRAL_SCALE)
    return SignalLabel.NEUTRAL, confidence, "within its normal range"
