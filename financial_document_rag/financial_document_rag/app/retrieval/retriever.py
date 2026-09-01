"""High-level semantic retrieval interface used by the API and by the
downstream Fundamental Agent (via the /retrieve endpoint)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from app.config import MAX_TOP_K
from app.models.schemas import RetrievalResult, SourceAttribution
from app.retrieval.embeddings import EmbeddingError, EmbeddingService
from app.retrieval.vector_store import VectorStore, VectorStoreError


class RetrieverError(Exception):
    """Raised for invalid retriever input (e.g. empty query, bad top_k)."""


class Retriever:
    """Ties together the EmbeddingService and VectorStore to answer natural
    language financial queries with fully-attributed results."""

    def __init__(self, embedding_service: Optional[EmbeddingService] = None,
                 vector_store: Optional[VectorStore] = None):
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()

    def retrieve(
        self,
        query: str,
        symbol: Optional[str] = None,
        document_type: Optional[str] = None,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        if not query or not query.strip():
            raise RetrieverError("Query must not be empty.")
        if not (1 <= top_k <= MAX_TOP_K):
            raise RetrieverError(f"top_k must be between 1 and {MAX_TOP_K}.")

        normalized_symbol = symbol.strip().upper() if symbol else None

        try:
            query_embedding = self.embedding_service.embed_text(query.strip())
        except EmbeddingError as exc:
            raise RetrieverError(f"Failed to embed query: {exc}") from exc

        try:
            raw_results = self.vector_store.query(
                query_embedding=query_embedding,
                top_k=top_k,
                symbol=normalized_symbol,
                document_type=document_type,
            )
        except VectorStoreError as exc:
            # Propagate as-is; the API layer maps this to HTTP 503.
            raise exc

        results: list[RetrievalResult] = []
        for item in raw_results:
            metadata = item["metadata"]
            source = SourceAttribution(
                document_id=metadata["document_id"],
                title=metadata["title"],
                company=metadata["company"],
                symbol=metadata["symbol"],
                document_type=metadata["document_type"],
                section=metadata["section"],
                source_name=metadata["source_name"],
                source_type=metadata["source_type"],
                published_date=date.fromisoformat(metadata["published_date"]),
            )
            results.append(
                RetrievalResult(
                    chunk_id=item["chunk_id"],
                    text=item["text"],
                    similarity_score=item["similarity_score"],
                    source=source,
                )
            )
        return results
