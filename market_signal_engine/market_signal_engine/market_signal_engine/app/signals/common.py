"""Helpers shared by the three signal calculators.

Confidence is deterministic and follows one rule everywhere: a reading sitting
exactly on its classification boundary scores ``CONFIDENCE_AT_THRESHOLD`` (0.5),
and confidence rises linearly toward 1.0 as the reading moves further away from
that boundary -- in whichever direction its classification points.
"""

from __future__ import annotations

from typing import Optional

from app.config import CONFIDENCE_AT_THRESHOLD, CONFIDENCE_DECIMALS, VALUE_DECIMALS
from app.models.schemas import SignalLabel, SignalResult


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Constrain ``value`` to [lower, upper]."""
    return max(lower, min(upper, value))


def scaled_confidence(distance: float, full_scale: float) -> float:
    """Map a distance from the classification boundary onto [0.5, 1.0].

    ``distance`` is how far the reading sits past (for directional signals) or
    away from (for neutral signals) the boundary. ``full_scale`` is the distance
    at which confidence reaches 1.0.
    """
    if full_scale <= 0:
        return CONFIDENCE_AT_THRESHOLD
    fraction = clamp(distance / full_scale)
    confidence = CONFIDENCE_AT_THRESHOLD + (1.0 - CONFIDENCE_AT_THRESHOLD) * fraction
    return clamp(confidence)


def round_confidence(value: float) -> float:
    return round(clamp(value), CONFIDENCE_DECIMALS)


def round_value(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(float(value), VALUE_DECIMALS)


def unavailable(name: str, reason: str) -> SignalResult:
    """Build the standard result for a dimension that could not be calculated.

    Confidence is 0.0 -- we never fabricate a number for data we do not have.
    """
    return SignalResult(
        name=name,
        signal=SignalLabel.UNAVAILABLE,
        value=None,
        confidence=0.0,
        evidence=[reason],
    )
