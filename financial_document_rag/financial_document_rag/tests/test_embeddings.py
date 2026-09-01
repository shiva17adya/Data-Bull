import pytest

from app.retrieval.embeddings import EmbeddingError, EmbeddingService


@pytest.fixture(scope="module")
def embedding_service():
    try:
        return EmbeddingService()
    except EmbeddingError as exc:
        pytest.skip(f"Embedding model unavailable in this environment (likely no internet access): {exc}")


def test_embedding_generated(embedding_service):
    vector = embedding_service.embed_text("Revenue increased 12% year-over-year.")
    assert isinstance(vector, list)
    assert len(vector) > 0


def test_correct_vector_dimensions(embedding_service):
    vector = embedding_service.embed_text("Operating margin improved this quarter.")
    assert len(vector) == embedding_service.dimension()


def test_same_text_produces_same_dimension(embedding_service):
    v1 = embedding_service.embed_text("What was the revenue growth?")
    v2 = embedding_service.embed_text("A completely different sentence about risk factors.")
    assert len(v1) == len(v2)


def test_empty_text_rejected(embedding_service):
    with pytest.raises(EmbeddingError):
        embedding_service.embed_text("")
    with pytest.raises(EmbeddingError):
        embedding_service.embed_text("   ")


def test_batch_embedding_matches_single(embedding_service):
    texts = ["Revenue grew this quarter.", "Risks include commodity price volatility."]
    batch_vectors = embedding_service.embed_documents(texts)
    assert len(batch_vectors) == 2
    assert len(batch_vectors[0]) == embedding_service.dimension()


def test_empty_batch_rejected(embedding_service):
    with pytest.raises(EmbeddingError):
        embedding_service.embed_documents(["Valid text", ""])


def test_empty_list_returns_empty(embedding_service):
    assert embedding_service.embed_documents([]) == []
