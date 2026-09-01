"""Application entrypoint.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import SERVICE_NAME, SERVICE_VERSION
from app.data.provider import SymbolNotFoundError
from app.models.schemas import ErrorDetail, ErrorResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

DESCRIPTION = """
Deterministic market signal engine for the multi-agent financial intelligence system.

Evaluates market data across three independent dimensions -- price momentum,
volume anomaly and RSI -- and returns a classified signal with a confidence
score and numerical evidence for every dimension.

This service produces analytical market signals. It does not produce
personalised investment advice or buy/sell instructions.
"""

app = FastAPI(
    title="Market Signal Engine",
    description=DESCRIPTION,
    version=SERVICE_VERSION,
)

app.include_router(router)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    """Build the standard error envelope."""
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@app.exception_handler(SymbolNotFoundError)
async def symbol_not_found_handler(request: Request, exc: SymbolNotFoundError) -> JSONResponse:
    logger.warning("invalid_symbol symbol=%s", exc.symbol)
    return _error(404, "SYMBOL_NOT_FOUND", str(exc))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    detail = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(part) for part in detail.get("loc", []) if part != "query")
    message = detail.get("msg", "Request parameters failed validation.")
    full_message = f"{location}: {message}" if location else message
    logger.warning("invalid_request detail=%s", full_message)
    return _error(422, "INVALID_REQUEST", full_message)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last line of defence: log the trace, return a clean envelope."""
    logger.exception("unhandled_error path=%s", request.url.path)
    return _error(
        500,
        "INTERNAL_ERROR",
        "An unexpected error occurred while processing the request.",
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "docs": "/docs",
        "main_endpoint": "/signals/{symbol}",
    }
