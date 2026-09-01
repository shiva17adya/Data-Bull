import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.retrieval.retriever import Retriever


@pytest.fixture
def client(populated_vector_store, fake_embedding_service):
    # Note: TestClient is intentionally used WITHOUT a `with` block here.
    # `with TestClient(app)` triggers FastAPI's startup lifespan event, which
    # would load the real sentence-transformers model (requiring network
    # access) and overwrite our injected fake retriever. Skipping the
    # context-manager form means the startup event never fires, so the fake,
    # offline retriever we set below is what the app actually uses.
    app.state.retriever = Retriever(
        embedding_service=fake_embedding_service, vector_store=populated_vector_store
    )
    test_client = TestClient(app)
    yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "financial-document-rag"


def test_retrieve_valid_query(client):
    response = client.post(
        "/retrieve",
        json={"query": "What was Reliance revenue growth?", "symbol": "RELIANCE", "top_k": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["query"] == "What was Reliance revenue growth?"
    assert len(body["results"]) > 0
    result = body["results"][0]
    assert "similarity_score" in result
    source = result["source"]
    for field in [
        "document_id", "title", "company", "symbol", "document_type",
        "section", "source_name", "source_type", "published_date",
    ]:
        assert field in source


def test_retrieve_with_document_type_filter(client):
    response = client.post(
        "/retrieve",
        json={"query": "revenue growth", "document_type": "annual_report", "top_k": 3},
    )
    assert response.status_code == 200
    body = response.json()
    for result in body["results"]:
        assert result["source"]["document_type"] == "annual_report"


def test_retrieve_empty_query_returns_400(client):
    response = client.post("/retrieve", json={"query": "", "top_k": 5})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_QUERY"


def test_retrieve_unknown_symbol_returns_no_results(client):
    response = client.post(
        "/retrieve", json={"query": "What was revenue growth?", "symbol": "INFY", "top_k": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NO_RESULTS"
    assert body["results"] == []
    assert any("INFY" in w for w in body["warnings"])


def test_retrieve_invalid_top_k_returns_400(client):
    response = client.post("/retrieve", json={"query": "revenue growth", "top_k": 0})
    assert response.status_code == 400

    response = client.post("/retrieve", json={"query": "revenue growth", "top_k": 11})
    assert response.status_code == 400


def test_documents_endpoint(client):
    response = client.get("/documents")
    assert response.status_code == 200
    body = response.json()
    assert body["total_documents"] == 6
    assert set(body["symbols"]) == {"RELIANCE", "TCS"}
