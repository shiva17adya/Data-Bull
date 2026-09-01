"""Runs the full ingestion pipeline: load -> chunk -> embed -> store.

Usage:
    python -m app.ingestion.ingest
"""
from __future__ import annotations

import logging

from app.ingestion.chunker import DocumentChunker
from app.ingestion.loader import DocumentLoader
from app.retrieval.embeddings import EmbeddingService
from app.retrieval.vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class IngestionService:
    """Coordinates the ingestion pipeline for the bundled financial corpus."""

    def __init__(
        self,
        loader: DocumentLoader | None = None,
        chunker: DocumentChunker | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.loader = loader or DocumentLoader()
        self.chunker = chunker or DocumentChunker()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()

    def ingest(self) -> dict:
        """Run the full pipeline. Returns a summary dict. Never raises for
        malformed individual documents (they are skipped and reported)."""
        documents = self.loader.load_all()
        if self.loader.issues:
            for issue in self.loader.issues:
                logger.warning("Skipped %s: %s", issue.file_path, issue.reason)

        chunks = self.chunker.chunk_documents(documents)

        inserted = 0
        if chunks:
            # Embed title + section context alongside the chunk body. This
            # improves retrieval quality (e.g. a query about "outlook"
            # matches the Management Outlook section even when the word
            # "outlook" itself doesn't appear in the body text). The raw
            # chunk.text (without this prefix) is what gets stored/displayed.
            texts_for_embedding = [f"{c.title}. {c.section}. {c.text}" for c in chunks]
            embeddings = self.embedding_service.embed_documents(texts_for_embedding)
            inserted = self.vector_store.add_chunks(chunks, embeddings)

        summary = {
            "documents_loaded": len(documents),
            "documents_skipped": len(self.loader.issues),
            "chunks_created": len(chunks),
            "chunks_inserted": inserted,
            "chunks_already_indexed": len(chunks) - inserted,
            "total_chunks_in_store": self.vector_store.count(),
        }
        return summary


def main() -> None:
    service = IngestionService()
    summary = service.ingest()
    logger.info("Ingestion summary: %s", summary)


if __name__ == "__main__":
    main()
