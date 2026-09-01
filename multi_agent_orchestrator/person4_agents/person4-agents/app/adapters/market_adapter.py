"""
Market signal boundary.

Person 4 never imports the signal engine directly. Anyone owning market data
implements `MarketSignalProvider` and passes it in.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

MOCK_PATH = Path(__file__).resolve().parents[2] / "mocks" / "market_data.json"


@runtime_checkable
class MarketSignalProvider(Protocol):
    """Supplies pre-computed technical indicators for a symbol.

    The Technical Agent *interprets* these values; it does not recompute them.

    Expected shape (all keys optional — missing keys degrade quality, they
    do not crash the agent):

        {
          "symbol": "RELIANCE",
          "as_of": "2026-02-14T10:15:00+05:30",
          "price": 1412.30,
          "indicators": {
            "rsi_14": 61.4,
            "momentum_5d_pct": 3.2,
            "momentum_20d_pct": 7.8,
            "volume_ratio_20d": 1.9,
            "sma_20": 1380.0,
            "sma_50": 1341.0,
            "sma_200": 1288.0,
            "macd_histogram": 4.6,
            "atr_pct": 1.8,
            "volatility_30d_pct": 22.0
          },
          "feed_status": "ok"
        }
    """

    async def get_signals(self, symbol: str) -> dict[str, Any]:
        ...


class MockMarketSignalProvider:
    """Loads `mocks/market_data.json`. Replaceable by Person 5 / data owner."""

    def __init__(self, path: str | Path = MOCK_PATH, override: dict[str, Any] | None = None):
        self.path = Path(path)
        self.override = override

    async def get_signals(self, symbol: str) -> dict[str, Any]:
        if self.override is not None:
            return self.override
        with self.path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get(symbol.upper(), data.get("RELIANCE", {}))


class StaticMarketSignalProvider:
    """Wraps a dict that was already fetched elsewhere (used by `analyze`)."""

    def __init__(self, payload: dict[str, Any] | None):
        self.payload = payload or {}

    async def get_signals(self, symbol: str) -> dict[str, Any]:
        return self.payload
