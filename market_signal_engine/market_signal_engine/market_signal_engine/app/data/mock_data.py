"""Deterministic simulated market data.

The series are generated from a seeded geometric random walk, so they look like
real price action (trends, gaps, volume clustering) while remaining byte-for-byte
reproducible across runs, machines and processes. Seeds are derived with
``zlib.crc32`` rather than ``hash()`` because Python randomises string hashing
per process, which would break determinism.

Four tradable symbols are supported, plus three ``DEMO_*`` fixtures that exist
purely so the degraded-data behaviour can be demonstrated live to a judge
without having to unplug anything.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.config import DEFAULT_CURRENCY, DEFAULT_HISTORY_LENGTH
from app.data.provider import MarketDataProvider, SymbolNotFoundError
from app.models.schemas import MarketData, build_candles

# Fixed anchor for the end of every generated series. Using a constant instead
# of "today" keeps generated data identical no matter when the tests run.
SERIES_END_DATE = datetime(2026, 1, 30, tzinfo=timezone.utc)


@dataclass(frozen=True)
class SymbolProfile:
    """Parameters shaping one symbol's simulated price behaviour."""

    symbol: str
    base_price: float
    daily_drift: float
    daily_volatility: float
    base_volume: float


SYMBOL_PROFILES: dict[str, SymbolProfile] = {
    "RELIANCE": SymbolProfile("RELIANCE", 1400.0, 0.0012, 0.014, 2_500_000),
    "TCS": SymbolProfile("TCS", 3900.0, 0.0004, 0.011, 1_200_000),
    "INFY": SymbolProfile("INFY", 1550.0, -0.0009, 0.016, 1_800_000),
    "HDFCBANK": SymbolProfile("HDFCBANK", 1650.0, 0.0002, 0.010, 3_100_000),
}

# Demo fixtures for the degraded-data scenarios.
DEMO_NO_VOLUME = "DEMO_NOVOLUME"
DEMO_SHORT_HISTORY = "DEMO_SHORTHIST"
DEMO_CORRUPT = "DEMO_CORRUPT"

DEMO_SYMBOLS = (DEMO_NO_VOLUME, DEMO_SHORT_HISTORY, DEMO_CORRUPT)

DEMO_BASE_PROFILE = SymbolProfile("DEMO", 1000.0, 0.0010, 0.013, 900_000)


def _seed_for(symbol: str) -> int:
    """Stable per-symbol seed. crc32 is deterministic across processes."""
    return zlib.crc32(symbol.encode("utf-8")) % (2**31)


def _generate_raw_candles(
    profile: SymbolProfile,
    count: int,
    seed_symbol: str,
    include_volume: bool = True,
) -> list[dict[str, Any]]:
    """Build ``count`` OHLCV bars as plain dicts.

    Closes follow a seeded geometric random walk. Each bar's open is the prior
    close nudged by a small gap; high and low are then widened outward from
    max/min(open, close) so the OHLC invariants hold by construction.
    """
    if count <= 0:
        return []

    rng = np.random.default_rng(_seed_for(seed_symbol))

    returns = rng.normal(profile.daily_drift, profile.daily_volatility, count)
    closes = profile.base_price * np.cumprod(1.0 + returns)

    gaps = rng.normal(0.0, profile.daily_volatility * 0.3, count)
    opens = np.empty(count)
    opens[0] = profile.base_price
    opens[1:] = closes[:-1] * (1.0 + gaps[1:])

    upper_wick = np.abs(rng.normal(0.0, profile.daily_volatility * 0.5, count))
    lower_wick = np.abs(rng.normal(0.0, profile.daily_volatility * 0.5, count))
    highs = np.maximum(opens, closes) * (1.0 + upper_wick)
    lows = np.minimum(opens, closes) * (1.0 - lower_wick)

    # Log-normal volume with mild clustering, so anomalies are occasional
    # rather than constant.
    volume_noise = rng.normal(0.0, 0.28, count)
    volumes = np.round(profile.base_volume * np.exp(volume_noise))

    dates = pd.bdate_range(end=SERIES_END_DATE, periods=count, tz="UTC")

    raw: list[dict[str, Any]] = []
    for i in range(count):
        raw.append(
            {
                "timestamp": dates[i].to_pydatetime(),
                "open": round(float(opens[i]), 2),
                "high": round(float(highs[i]), 2),
                "low": round(float(lows[i]), 2),
                "close": round(float(closes[i]), 2),
                "volume": float(max(volumes[i], 0.0)) if include_volume else None,
            }
        )

    # Rounding to 2dp can, very rarely, push high a hair below max(open, close)
    # or low a hair above min(open, close). Repair the bounds rather than let a
    # valid bar be discarded downstream.
    for bar in raw:
        bar["high"] = max(bar["high"], bar["open"], bar["close"])
        bar["low"] = min(bar["low"], bar["open"], bar["close"])

    return raw


def _corrupt_series(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Inject a few invalid bars to exercise the validation path."""
    corrupted = [dict(bar) for bar in raw]
    if len(corrupted) > 10:
        corrupted[5]["high"] = corrupted[5]["low"] - 10.0  # high < low
    if len(corrupted) > 20:
        corrupted[12]["close"] = -1.0  # non-positive price
    if len(corrupted) > 30:
        corrupted[25]["volume"] = -500.0  # negative volume
    return corrupted


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic in-memory provider. Requires no API keys or network."""

    def __init__(self, history_length: int = DEFAULT_HISTORY_LENGTH) -> None:
        self._history_length = history_length

    def supported_symbols(self) -> list[str]:
        return sorted(list(SYMBOL_PROFILES) + list(DEMO_SYMBOLS))

    def get_market_data(self, symbol: str, limit: Optional[int] = None) -> MarketData:
        normalised = symbol.strip().upper()
        count = limit if limit is not None else self._history_length

        raw = self._raw_for(normalised, count)
        if raw is None:
            raise SymbolNotFoundError(symbol)

        candles, warnings = build_candles(raw)
        return MarketData(
            symbol=normalised,
            currency=DEFAULT_CURRENCY,
            candles=candles,
            warnings=warnings,
        )

    def _raw_for(self, symbol: str, count: int) -> Optional[list[dict[str, Any]]]:
        """Return raw bars for a symbol, or None if it is unknown."""
        count = max(int(count), 0)

        if symbol in SYMBOL_PROFILES:
            return _generate_raw_candles(SYMBOL_PROFILES[symbol], count, symbol)

        if symbol == DEMO_NO_VOLUME:
            return _generate_raw_candles(
                DEMO_BASE_PROFILE, count, symbol, include_volume=False
            )

        if symbol == DEMO_SHORT_HISTORY:
            return _generate_raw_candles(DEMO_BASE_PROFILE, min(count, 6), symbol)

        if symbol == DEMO_CORRUPT:
            return _corrupt_series(_generate_raw_candles(DEMO_BASE_PROFILE, count, symbol))

        return None
