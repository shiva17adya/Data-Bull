"""Persistent ChromaDB-backed vector store for financial document chunks."""
from __future__ import annotations

import logging
from typing import Optional

from app.config import CHROMA_PATH, COLLECTION_NAME
from app.models.schemas import Chunk

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Raised when the underlying vector database is unavailable or fails."""


class VectorStore:
    """Thin wrapper around a persistent Chroma collection.

    Metadata stored per chunk: chunk_id, document_id, company, symbol,
    document_type, title, section, source_name, source_type, published_date.
    """

    def __init__(self, path: Optional[str] = None, collection_name: str = COLLECTION_NAME):
        self.path = path or CHROMA_PATH
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._connect()

    def _connect(self) -> None:
        try:
            import chromadb

            self._client = chromadb.PersistentClient(path=self.path)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            raise VectorStoreError(f"Could not connect to Chroma at '{self.path}': {exc}") from exc

    @staticmethod
    def _chunk_metadata(chunk: Chunk) -> dict:
        return {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "company": chunk.company,
            "symbol": chunk.symbol,
            "document_type": chunk.document_type,
            "title": chunk.title,
            "section": chunk.section,
            "source_name": chunk.source_name,
            "source_type": chunk.source_type,
            "published_date": chunk.published_date.isoformat(),
        }

    def add_chunks(self, chunks: list[Chunk], embeddings: Optional[list[list[float]]] = None) -> int:
        """Add chunks (with pre-computed embeddings) to the collection.

        Chunks whose chunk_id already exists in the collection are skipped, so
        repeated ingestion runs do not create duplicates. Returns the number of
        chunks actually inserted.
        """
        if not chunks:
            return 0
        if embeddings is None or len(embeddings) != len(chunks):
            raise VectorStoreError("embeddings must be provided and match chunks length.")

        existing_ids: set[str] = set()
        try:
            existing = self._collection.get(ids=[c.chunk_id for c in chunks])
            existing_ids = set(existing.get("ids", []))
        except Exception as exc:
            raise VectorStoreError(f"Failed to check existing chunk ids: {exc}") from exc

        new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]
        new_embeddings = [e for c, e in zip(chunks, embeddings) if c.chunk_id not in existing_ids]

        if not new_chunks:
            return 0

        try:
            self._collection.add(
                ids=[c.chunk_id for c in new_chunks],
                embeddings=new_embeddings,
                documents=[c.text for c in new_chunks],
                metadatas=[self._chunk_metadata(c) for c in new_chunks],
            )
        except Exception as exc:
            raise VectorStoreError(f"Failed to add chunks to Chroma: {exc}") from exc

        return len(new_chunks)

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        symbol: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> list[dict]:
        """Query the collection for the top_k most similar chunks. Returns a
        list of dicts with chunk_id, text, similarity_score, metadata."""
        where_clause = None
        conditions = []
        if symbol:
            conditions.append({"symbol": symbol})
        if document_type:
            conditions.append({"document_type": document_type})
        if len(conditions) == 1:
            where_clause = conditions[0]
        elif len(conditions) > 1:
            where_clause = {"$and": conditions}

        try:
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
            )
        except Exception as exc:
            raise VectorStoreError(f"Chroma query failed: {exc}") from exc

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        output = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            # Chroma cosine distance -> similarity score in [0, 1] (approx).
            similarity_score = max(0.0, 1.0 - distance)
            output.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "similarity_score": round(similarity_score, 4),
                    "metadata": metadata,
                }
            )
        return output

    def count(self) -> int:
        try:
            return self._collection.count()
        except Exception as exc:
            raise VectorStoreError(f"Failed to count chunks: {exc}") from exc

    def reset(self) -> None:
        """Delete and recreate the collection (used mainly by tests)."""
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass  # collection may not exist yet
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
