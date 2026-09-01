"""Shared pytest fixtures.

Most tests use a deterministic, offline FakeEmbeddingService instead of the
real sentence-transformers model so the test suite runs without network
access. The FakeEmbeddingService builds a bag-of-words style vector so that
chunks sharing vocabulary with a query score more similar than unrelated
chunks -- good enough to exercise retrieval logic deterministically.

test_embeddings.py additionally exercises the REAL EmbeddingService and will
skip itself if the embedding model cannot be downloaded in the current
environment (e.g. no internet access to huggingface.co).
"""
from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

import pytest

from app.retrieval.vector_store import VectorStore

FAKE_EMBEDDING_DIM = 64


class FakeEmbeddingService:
    """Deterministic, offline stand-in for EmbeddingService.

    Produces a bag-of-words hashed vector: each word deterministically votes
    for one dimension. Cosine similarity between two texts then roughly
    tracks vocabulary overlap, which is sufficient to validate that our
    retrieval plumbing (query -> embed -> vector store -> ranked results)
    behaves sensibly without needing a real transformer model or internet
    access.
    """

    def __init__(self, dim: int = FAKE_EMBEDDING_DIM):
        self.dim = dim

    def _vector_for(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        words = [w.lower().strip(".,;:()") for w in text.split()]
        for word in words:
            if not word:
                continue
            idx = int(hashlib.sha1(word.encode("utf-8")).hexdigest(), 16) % self.dim
            vector[idx] += 1.0
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    def embed_text(self, text: str) -> list[float]:
        if text is None or not text.strip():
            from app.retrieval.embeddings import EmbeddingError

            raise EmbeddingError("Cannot embed empty text.")
        return self._vector_for(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]

    def dimension(self) -> int:
        return self.dim


@pytest.fixture
def fake_embedding_service() -> FakeEmbeddingService:
    return FakeEmbeddingService()


@pytest.fixture
def temp_chroma_path():
    """Isolated, temporary Chroma directory so tests never touch the real
    persisted index used by the running API/demo."""
    path = tempfile.mkdtemp(prefix="chroma_test_")
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def empty_vector_store(temp_chroma_path):
    store = VectorStore(path=temp_chroma_path, collection_name="test_financial_documents")
    yield store


@pytest.fixture
def populated_vector_store(temp_chroma_path, fake_embedding_service):
    """A vector store pre-loaded with the full bundled corpus, using the fake
    embedding service so no network access is required."""
    from app.ingestion.chunker import DocumentChunker
    from app.ingestion.loader import DocumentLoader

    loader = DocumentLoader()
    documents = loader.load_all()
    chunker = DocumentChunker()
    chunks = chunker.chunk_documents(documents)

    store = VectorStore(path=temp_chroma_path, collection_name="test_financial_documents")
    texts_for_embedding = [f"{c.title}. {c.section}. {c.text}" for c in chunks]
    embeddings = fake_embedding_service.embed_documents(texts_for_embedding)
    store.add_chunks(chunks, embeddings)
    return store


@pytest.fixture
def sample_corpus_dir():
    return Path(__file__).resolve().parent.parent / "app" / "documents" / "corpus"
