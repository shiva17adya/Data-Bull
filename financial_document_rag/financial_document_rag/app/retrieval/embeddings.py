"""Wraps a sentence-transformers model so it is loaded once and reused."""
from __future__ import annotations

import logging
import threading

from app.config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when text embedding fails for a controllable, expected reason."""


class EmbeddingService:
    """Loads a SentenceTransformer model once (per process) and reuses it for
    both single-text and batch embedding requests."""

    _model = None
    _model_lock = threading.Lock()

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self._ensure_model_loaded()

    def _ensure_model_loaded(self) -> None:
        if EmbeddingService._model is not None:
            return
        with EmbeddingService._model_lock:
            if EmbeddingService._model is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    logger.info("Loading embedding model: %s", self.model_name)
                    EmbeddingService._model = SentenceTransformer(self.model_name)
                except Exception as exc:  # pragma: no cover - environment dependent
                    raise EmbeddingError(f"Failed to load embedding model: {exc}") from exc

    def embed_text(self, text: str) -> list[float]:
        if text is None or not text.strip():
            raise EmbeddingError("Cannot embed empty text.")
        try:
            vector = EmbeddingService._model.encode(text, show_progress_bar=False)
        except Exception as exc:
            raise EmbeddingError(f"Embedding failed: {exc}") from exc
        return vector.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        cleaned = [t for t in texts]
        for t in cleaned:
            if t is None or not t.strip():
                raise EmbeddingError("Cannot embed empty text in batch.")
        try:
            vectors = EmbeddingService._model.encode(cleaned, show_progress_bar=False)
        except Exception as exc:
            raise EmbeddingError(f"Batch embedding failed: {exc}") from exc
        return [v.tolist() for v in vectors]

    def dimension(self) -> int:
        return EmbeddingService._model.get_sentence_embedding_dimension()
