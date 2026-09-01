"""Market data provider abstraction.

The signal engine depends on this interface, never on a concrete data source.
Swapping the mock provider for a live NSE/broker feed later means writing one
new class that satisfies ``MarketDataProvider`` -- no signal code changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.config import DEFAULT_HISTORY_LENGTH
from app.models.schemas import MarketCandle, MarketData


class SymbolNotFoundError(LookupError):
    """Raised when a provider has no data for the requested symbol."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"No market data available for symbol {symbol}.")


class MarketDataProvider(ABC):
    """Interface every market data source must satisfy."""

    @abstractmethod
    def get_market_data(self, symbol: str, limit: int = DEFAULT_HISTORY_LENGTH) -> MarketData:
        """Return validated market data for ``symbol``.

        Raises:
            SymbolNotFoundError: if the symbol is not supported by this provider.
        """

    @abstractmethod
    def supported_symbols(self) -> list[str]:
        """Return the sorted list of symbols this provider can serve."""

    def get_historical_data(
        self, symbol: str, limit: int = DEFAULT_HISTORY_LENGTH
    ) -> list[MarketCandle]:
        """Convenience accessor returning only the candle series."""
        return self.get_market_data(symbol, limit=limit).candles
