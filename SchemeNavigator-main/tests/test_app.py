import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_status_endpoint():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data

def test_list_history():
    response = client.get("/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)