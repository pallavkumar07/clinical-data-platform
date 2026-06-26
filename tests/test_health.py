"""Tests for the health and root endpoints."""

from fastapi.testclient import TestClient

from clinical_data_platform.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_root_returns_welcome():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
