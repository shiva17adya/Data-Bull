"""FastAPI application entrypoint for the financial_document_rag module.

Run with:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.models.schemas import ErrorDetail, ErrorResponse
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import VectorStoreError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Financial Document RAG",
    description=(
        "Semantic retrieval over a synthetic corpus of financial documents. "
        "Serves attributed evidence to the downstream Fundamental Agent."
    ),
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        app.state.retriever = Retriever()
        logger.info("Retriever initialized. Indexed chunks: %s", app.state.retriever.vector_store.count())
    except VectorStoreError as exc:
        # Do not crash the whole app; endpoints will surface 503 on use.
        logger.error("Vector store failed to initialize at startup: %s", exc)
        app.state.retriever = None


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Translate Pydantic validation errors (e.g. empty query, bad top_k) into
    the module's standard error envelope instead of FastAPI's default 422 body."""
    messages = []
    for err in exc.errors():
        messages.append(err.get("msg", "Invalid request."))
    combined_message = "; ".join(messages) if messages else "Invalid request."

    code = "INVALID_QUERY" if any("query" in str(e.get("loc", "")) for e in exc.errors()) else "INVALID_REQUEST"
    body = ErrorResponse(error=ErrorDetail(code=code, message=combined_message))
    return JSONResponse(status_code=400, content=body.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    body = ErrorResponse(
        error=ErrorDetail(code="INTERNAL_ERROR", message="An unexpected error occurred.")
    )
    return JSONResponse(status_code=500, content=body.model_dump())


app.include_router(router)
