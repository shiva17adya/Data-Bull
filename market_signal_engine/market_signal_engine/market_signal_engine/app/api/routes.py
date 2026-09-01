"""HTTP routes. This API is the stable integration boundary for the team."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Path, Query

from app.config import (
    MOMENTUM_LOOKBACK,
    MOMENTUM_LOOKBACK_MAX,
    MOMENTUM_LOOKBACK_MIN,
    SERVICE_NAME,
)
from app.data.mock_data import MockMarketDataProvider
from app.models.schemas import (
    ErrorResponse,
    HealthResponse,
    MarketDataResponse,
    SignalResponse,
    utc_now,
)
from app.signals.engine import SignalEngine, market_data_status

logger = logging.getLogger(__name__)

router = APIRouter()

# A single engine instance is reused across requests. It is stateless, so this
# is safe and avoids regenerating mock series on every call.
_engine = SignalEngine(MockMarketDataProvider())


def get_engine() -> SignalEngine:
    """Dependency hook so tests can inject an alternative provider."""
    return _engine


ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Symbol not found"},
    422: {"model": ErrorResponse, "description": "Invalid request parameters"},
}


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(status="healthy", service=SERVICE_NAME)


@router.get(
    "/market/{symbol}",
    response_model=MarketDataResponse,
    responses=ERROR_RESPONSES,
    tags=["market"],
)
def get_market(
    symbol: str = Path(..., description="Ticker symbol, e.g. RELIANCE"),
    engine: SignalEngine = Depends(get_engine),
) -> MarketDataResponse:
    """Latest OHLCV snapshot for a symbol, with no signal calculation."""
    market_data = engine.provider.get_market_data(symbol)
    return MarketDataResponse(
        symbol=market_data.symbol,
        timestamp=utc_now(),
        market_data=market_data.snapshot(),
        candle_count=len(market_data.candles),
        data_status=market_data_status(market_data),
        warnings=market_data.warnings,
    )


@router.get(
    "/signals/{symbol}",
    response_model=SignalResponse,
    responses=ERROR_RESPONSES,
    tags=["signals"],
)
def get_signals(
    symbol: str = Path(..., description="Ticker symbol, e.g. RELIANCE"),
    lookback: int = Query(
        MOMENTUM_LOOKBACK,
        ge=MOMENTUM_LOOKBACK_MIN,
        le=MOMENTUM_LOOKBACK_MAX,
        description="Momentum lookback period in candles.",
    ),
    engine: SignalEngine = Depends(get_engine),
) -> SignalResponse:
    """Main integration endpoint: full three-dimension signal analysis.

    Downstream consumers should read ``overall_signal``, ``confidence``,
    ``signals``, ``reasoning``, ``market_data``, ``data_status`` and ``warnings``.
    """
    return engine.analyze(symbol, lookback=lookback)


@router.get("/symbols", response_model=list[str], tags=["market"])
def list_symbols(engine: SignalEngine = Depends(get_engine)) -> list[str]:
    """Symbols the configured provider can serve."""
    return engine.provider.supported_symbols()
