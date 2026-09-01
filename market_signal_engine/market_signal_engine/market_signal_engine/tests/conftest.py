"""Shared test helpers.

Every helper builds candles from explicit numbers -- no randomness anywhere in
the test suite, so failures are always reproducible.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

import pytest

from app.models.schemas import MarketCandle, MarketData

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_candle(
    close: float,
    volume: Optional[float] = 1_000_000.0,
    index: int = 0,
    spread: float = 1.0,
) -> MarketCandle:
    """Build one valid candle around a given close price."""
    open_price = close
    return MarketCandle(
        timestamp=BASE_TIME + timedelta(days=index),
        open=open_price,
        high=max(open_price, close) + spread,
        low=min(open_price, close) - spread,
        close=close,
        volume=volume,
    )


def make_candles(
    closes: Sequence[float],
    volumes: Optional[Sequence[Optional[float]]] = None,
) -> list[MarketCandle]:
    """Build a candle series from explicit closes and optional volumes."""
    if volumes is None:
        volumes = [1_000_000.0] * len(closes)
    if len(volumes) != len(closes):
        raise ValueError("closes and volumes must be the same length")

    return [
        make_candle(close=close, volume=volume, index=i)
        for i, (close, volume) in enumerate(zip(closes, volumes))
    ]


def flat_series(value: float, count: int, volume: Optional[float] = 1_000_000.0):
    """A constant-price series of ``count`` candles."""
    return make_candles([value] * count, [volume] * count)


def market_data(candles, symbol: str = "TEST", warnings: Optional[list[str]] = None) -> MarketData:
    return MarketData(symbol=symbol, candles=candles, warnings=warnings or [])


@pytest.fixture
def rising_closes() -> list[float]:
    """40 candles rising ~1% per bar."""
    closes = [100.0]
    for _ in range(39):
        closes.append(round(closes[-1] * 1.01, 4))
    return closes


@pytest.fixture
def falling_closes() -> list[float]:
    """40 candles falling ~1% per bar."""
    closes = [100.0]
    for _ in range(39):
        closes.append(round(closes[-1] * 0.99, 4))
    return closes


@pytest.fixture
def choppy_closes() -> list[float]:
    """40 candles oscillating tightly around 100 -- no net direction."""
    return [100.0 + (0.2 if i % 2 else -0.2) for i in range(40)]
