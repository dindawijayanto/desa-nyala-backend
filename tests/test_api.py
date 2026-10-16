from fastapi.testclient import TestClient
from app.main import app
from tests.test_validation import sample_payload

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_input_validation_endpoint():
    response = client.post("/api/v1/inputs/validate", json=sample_payload())
    assert response.status_code == 200
    assert response.json()["estimated_daily_energy_kwh"] == 9.0


def test_optimization_endpoint_does_not_fake_results():
    response = client.post("/api/v1/optimizations", json=sample_payload())
    assert response.status_code in (422, 503)
    assert "detail" in response.json()
