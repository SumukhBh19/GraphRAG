import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_ping(client):
    res = client.get("/ping")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"

def test_get_graph(client):
    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "links" in data
    assert len(data["nodes"]) > 0

def test_get_graph_stats(client):
    res = client.get("/api/graph/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["nodes_count"] > 0
    assert "node_types" in data

def test_query_hybrid(client):
    res = client.post("/api/query", json={
        "query": "What are the asset allocation requirements for Multi Cap funds under SEBI?",
        "mode": "hybrid",
        "top_k": 3
    })
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert "citations" in data
    assert "subgraph" in data

def test_query_vanilla(client):
    res = client.post("/api/query", json={
        "query": "What are the priority sector lending targets under RBI?",
        "mode": "vanilla",
        "top_k": 3
    })
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert len(data["citations"]) > 0

def test_list_documents(client):
    res = client.get("/api/ingest/documents")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
