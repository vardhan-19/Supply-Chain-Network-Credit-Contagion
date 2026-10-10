import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "running"

def test_get_graph_topology(client):
    response = client.get("/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data and "links" in data
    assert len(data["nodes"]) == 174
    assert len(data["links"]) == 1213

    first_node = data["nodes"][0]
    assert "id" in first_node
    assert "name" in first_node
    assert "pd" in first_node
    assert "risk_tier" in first_node

def test_predict_endpoint(client):
    response = client.post("/predict")
    assert response.status_code == 200
    predictions = response.json()
    assert isinstance(predictions, list)
    assert len(predictions) == 174

    for item in predictions[:5]:
        assert "company_id" in item
        assert "company_name" in item
        assert 0.0 <= item["pd"] <= 1.0
        assert item["risk_tier"] in ("Low", "Medium", "High")

def test_simulate_node_removal(client):
    graph_res = client.get("/graph")
    nodes = graph_res.json()["nodes"]
    target_id = nodes[0]["id"]

    payload = {
        "target_company_id": target_id,
        "shock_type": "node_removal"
    }
    response = client.post("/simulate", json=payload)
    assert response.status_code == 200
    result = response.json()

    assert result["shocked_company"] == target_id
    assert result["shock_type"] == "node_removal"
    assert "total_systemic_loss_increase" in result
    assert "affected_nodes" in result
    assert result["total_systemic_loss_increase"] >= 0.0

def test_simulate_edge_removal(client):
    graph_res = client.get("/graph")
    links = graph_res.json()["links"]
    first_link = links[0]
    source_id = first_link["source"] if isinstance(first_link["source"], str) else first_link["source"]["id"]
    target_id = first_link["target"] if isinstance(first_link["target"], str) else first_link["target"]["id"]

    payload = {
        "target_company_id": target_id,
        "source_company_id": source_id,
        "shock_type": "edge_removal"
    }
    response = client.post("/simulate", json=payload)
    assert response.status_code == 200
    result = response.json()

    assert result["shocked_company"] == target_id
    assert result["source_company"] == source_id
    assert result["shock_type"] == "edge_removal"
    assert "total_systemic_loss_increase" in result

def test_simulate_edge_removal_missing_source(client):
    graph_res = client.get("/graph")
    target_id = graph_res.json()["nodes"][0]["id"]

    payload = {
        "target_company_id": target_id,
        "shock_type": "edge_removal"
    }
    response = client.post("/simulate", json=payload)
    assert response.status_code == 200
    assert "error" in response.json()

def test_simulate_empty_payload(client):
    response = client.post("/simulate", json={})
    assert response.status_code == 422
