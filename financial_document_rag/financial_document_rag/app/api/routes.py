"""API routes for the financial_document_rag retrieval service."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.ingestion.ingest import IngestionService
from app.models.schemas import (
    DocumentsInfoResponse,
    ErrorDetail,
    ErrorResponse,
    RetrievalRequest,
    RetrievalResponse,
)
from app.retrieval.retriever import Retriever, RetrieverError
from app.retrieval.vector_store import VectorStoreError

logger = logging.getLogger(__name__)
router = APIRouter()


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


@router.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": "financial-document-rag"}


@router.post("/retrieve", response_model=None)
def retrieve(payload: RetrievalRequest, request: Request):
    retriever: Retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        return _error_response(503, "VECTOR_STORE_UNAVAILABLE", "The retrieval index is currently unavailable.")

    try:
        results = retriever.retrieve(
            query=payload.query,
            symbol=payload.symbol,
            document_type=payload.document_type,
            top_k=payload.top_k,
        )
    except RetrieverError as exc:
        return _error_response(400, "INVALID_QUERY", str(exc))
    except VectorStoreError as exc:
        logger.error("Vector store unavailable: %s", exc)
        return _error_response(503, "VECTOR_STORE_UNAVAILABLE", "The retrieval index is currently unavailable.")
    except Exception as exc:  # pragma: no cover - defensive catch-all
        logger.exception("Unexpected retrieval error")
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred during retrieval.")

    warnings: list[str] = []
    status = "OK"
    if not results:
        status = "NO_RESULTS"
        if payload.symbol:
            warnings.append(f"No indexed documents were found for symbol {payload.symbol}.")
        else:
            warnings.append("No matching documents were found for this query.")

    response = RetrievalResponse(
        query=payload.query,
        symbol=payload.symbol,
        results=results,
        status=status,
        warnings=warnings,
    )
    return response.model_dump()


@router.get("/documents", response_model=DocumentsInfoResponse)
def documents(request: Request) -> DocumentsInfoResponse:
    retriever: Retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        return DocumentsInfoResponse(total_documents=0, symbols=[])
    try:
        collection = retriever.vector_store._collection
        all_items = collection.get()
        metadatas = all_items.get("metadatas", []) or []
        document_ids = {m.get("document_id") for m in metadatas if m.get("document_id")}
        symbols = sorted({m.get("symbol") for m in metadatas if m.get("symbol")})
        return DocumentsInfoResponse(total_documents=len(document_ids), symbols=symbols)
    except Exception as exc:
        logger.exception("Failed to read document info")
        return DocumentsInfoResponse(total_documents=0, symbols=[])


@router.post("/ingest")
def ingest(request: Request):
    """Ingest ONLY the bundled corpus shipped with this module. Does not accept
    arbitrary filesystem paths from API callers."""
    retriever: Retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        return _error_response(503, "VECTOR_STORE_UNAVAILABLE", "The retrieval index is currently unavailable.")
    try:
        service = IngestionService(
            embedding_service=retriever.embedding_service,
            vector_store=retriever.vector_store,
        )
        summary = service.ingest()
        return {"status": "OK", "summary": summary}
    except VectorStoreError as exc:
        return _error_response(503, "VECTOR_STORE_UNAVAILABLE", str(exc))
    except Exception as exc:
        logger.exception("Ingestion failed")
        return _error_response(500, "INGESTION_FAILED", "Ingestion failed due to an internal error.")
