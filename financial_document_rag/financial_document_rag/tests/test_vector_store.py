from datetime import date

from app.models.schemas import Chunk


def _make_chunk(chunk_id, symbol="RELIANCE", document_type="earnings_report", section="Revenue",
                 text="Revenue increased significantly this quarter."):
    return Chunk(
        chunk_id=chunk_id,
        document_id=f"{chunk_id}_doc",
        company="Test Co",
        symbol=symbol,
        document_type=document_type,
        title="Test Title",
        section=section,
        source_name="Test Source",
        source_type="synthetic",
        published_date=date(2026, 1, 1),
        text=text,
    )


def test_insertion_and_count(empty_vector_store, fake_embedding_service):
    chunks = [_make_chunk("c1"), _make_chunk("c2")]
    embeddings = fake_embedding_service.embed_documents([c.text for c in chunks])
    inserted = empty_vector_store.add_chunks(chunks, embeddings)
    assert inserted == 2
    assert empty_vector_store.count() == 2


def test_no_duplicate_insertion_on_rerun(empty_vector_store, fake_embedding_service):
    chunks = [_make_chunk("c1")]
    embeddings = fake_embedding_service.embed_documents([c.text for c in chunks])
    first = empty_vector_store.add_chunks(chunks, embeddings)
    second = empty_vector_store.add_chunks(chunks, embeddings)
    assert first == 1
    assert second == 0
    assert empty_vector_store.count() == 1


def test_retrieval_returns_metadata(empty_vector_store, fake_embedding_service):
    chunk = _make_chunk("c1", text="Revenue growth accelerated this quarter.")
    embeddings = fake_embedding_service.embed_documents([chunk.text])
    empty_vector_store.add_chunks([chunk], embeddings)

    query_embedding = fake_embedding_service.embed_text("What was revenue growth?")
    results = empty_vector_store.query(query_embedding, top_k=5)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"
    assert results[0]["metadata"]["symbol"] == "RELIANCE"
    assert results[0]["metadata"]["document_type"] == "earnings_report"
    assert "similarity_score" in results[0]


def test_symbol_filtering(empty_vector_store, fake_embedding_service):
    chunks = [
        _make_chunk("c1", symbol="RELIANCE", text="Reliance revenue grew this quarter."),
        _make_chunk("c2", symbol="TCS", text="TCS revenue grew this quarter."),
    ]
    embeddings = fake_embedding_service.embed_documents([c.text for c in chunks])
    empty_vector_store.add_chunks(chunks, embeddings)

    query_embedding = fake_embedding_service.embed_text("revenue grew this quarter")
    results = empty_vector_store.query(query_embedding, top_k=5, symbol="TCS")
    assert len(results) == 1
    assert results[0]["metadata"]["symbol"] == "TCS"


def test_document_type_filtering(empty_vector_store, fake_embedding_service):
    chunks = [
        _make_chunk("c1", document_type="earnings_report", text="Quarterly earnings report text."),
        _make_chunk("c2", document_type="annual_report", text="Annual report text."),
    ]
    embeddings = fake_embedding_service.embed_documents([c.text for c in chunks])
    empty_vector_store.add_chunks(chunks, embeddings)

    query_embedding = fake_embedding_service.embed_text("report text")
    results = empty_vector_store.query(query_embedding, top_k=5, document_type="annual_report")
    assert len(results) == 1
    assert results[0]["metadata"]["document_type"] == "annual_report"


def test_empty_collection_query_returns_no_results(empty_vector_store, fake_embedding_service):
    query_embedding = fake_embedding_service.embed_text("anything at all")
    results = empty_vector_store.query(query_embedding, top_k=5)
    assert results == []
    assert empty_vector_store.count() == 0
