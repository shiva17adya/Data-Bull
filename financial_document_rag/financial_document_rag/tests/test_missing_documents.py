from app.retrieval.retriever import Retriever


def test_unknown_symbol_yields_no_results_not_crash(populated_vector_store, fake_embedding_service):
    retriever = Retriever(embedding_service=fake_embedding_service, vector_store=populated_vector_store)
    results = retriever.retrieve(query="What was revenue growth?", symbol="INFY", top_k=5)
    assert results == []  # graceful NO_RESULTS behavior, no exception


def test_empty_index_yields_no_results_not_crash(empty_vector_store, fake_embedding_service):
    retriever = Retriever(embedding_service=fake_embedding_service, vector_store=empty_vector_store)
    results = retriever.retrieve(query="What was revenue growth?", top_k=5)
    assert results == []
