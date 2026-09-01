"""Pydantic v2 models defining the module's data structures and public contract.

The field names in ``SignalResponse`` are the integration boundary for the rest
of the team. They should not change after implementation.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from app.config import DEFAULT_CURRENCY


class SignalLabel(str, Enum):
    """Classification applied to a single dimension or to the overall result.

    ``UNAVAILABLE`` is only ever used for an individual dimension that could not
    be calculated. The overall signal is always one of the three directional
    labels.
    """

    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    UNAVAILABLE = "UNAVAILABLE"


class DataStatus(str, Enum):
    """Quality of the market data underlying a response."""

    OK = "OK"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


def _is_finite(value: float) -> bool:
    """Return True only for real, finite numbers (rejects NaN and +/-inf)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class MarketCandle(BaseModel):
    """A single OHLCV bar.

    Volume is optional because real feeds occasionally omit it. Every other
    field must be present, finite and strictly positive. Cross-field OHLC
    consistency is enforced -- obviously invalid bars are rejected rather than
    silently accepted.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None

    @field_validator("open", "high", "low", "close")
    @classmethod
    def _validate_price(cls, value: float) -> float:
        if not _is_finite(value):
            raise ValueError("price must be a finite number")
        if value <= 0:
            raise ValueError("price must be greater than zero")
        return float(value)

    @field_validator("volume")
    @classmethod
    def _validate_volume(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if not _is_finite(value):
            raise ValueError("volume must be a finite number or null")
        if value < 0:
            raise ValueError("volume must not be negative")
        return float(value)

    @model_validator(mode="after")
    def _validate_ohlc_consistency(self) -> "MarketCandle":
        if self.high < self.low:
            raise ValueError("high must not be below low")
        if self.high < max(self.open, self.close):
            raise ValueError("high must be at least max(open, close)")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be at most min(open, close)")
        return self


def build_candles(raw_items: Iterable[Any]) -> tuple[list[MarketCandle], list[str]]:
    """Validate raw candle data, discarding bad bars instead of crashing.

    Returns the valid candles (in input order) plus a human-readable warning for
    every bar that failed validation. This is the single choke point where
    untrusted provider data enters the system.
    """
    candles: list[MarketCandle] = []
    warnings: list[str] = []

    for index, item in enumerate(raw_items):
        if isinstance(item, MarketCandle):
            candles.append(item)
            continue
        try:
            candles.append(MarketCandle.model_validate(item))
        except (ValidationError, TypeError):
            warnings.append(f"Candle at index {index} contains invalid values and was discarded.")

    return candles, warnings


class MarketSnapshot(BaseModel):
    """The most recent bar, flattened for consumers that only need 'now'."""

    price: float
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    currency: str = DEFAULT_CURRENCY

    @classmethod
    def from_candle(cls, candle: MarketCandle, currency: str = DEFAULT_CURRENCY) -> "MarketSnapshot":
        return cls(
            price=candle.close,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            currency=currency,
        )


class MarketData(BaseModel):
    """Everything a provider returns for one symbol."""

    symbol: str
    currency: str = DEFAULT_CURRENCY
    candles: list[MarketCandle] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def latest_candle(self) -> Optional[MarketCandle]:
        return self.candles[-1] if self.candles else None

    def snapshot(self) -> Optional[MarketSnapshot]:
        candle = self.latest_candle
        if candle is None:
            return None
        return MarketSnapshot.from_candle(candle, self.currency)


class SignalResult(BaseModel):
    """One signal dimension. All three dimensions share this exact shape."""

    name: str
    signal: SignalLabel
    value: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class SignalResponse(BaseModel):
    """The main integration contract, returned by GET /signals/{symbol}."""

    symbol: str
    timestamp: datetime
    market_data: Optional[MarketSnapshot] = None
    signals: dict[str, SignalResult] = Field(default_factory=dict)
    overall_signal: SignalLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: list[str] = Field(default_factory=list)
    data_status: DataStatus
    warnings: list[str] = Field(default_factory=list)


class MarketDataResponse(BaseModel):
    """Returned by GET /market/{symbol}."""

    symbol: str
    timestamp: datetime
    market_data: Optional[MarketSnapshot] = None
    candle_count: int = 0
    data_status: DataStatus
    warnings: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Consistent error envelope. Stack traces are never exposed."""

    error: ErrorDetail


def utc_now() -> datetime:
    """Timezone-aware current UTC time, used for response timestamps."""
    return datetime.now(timezone.utc)
