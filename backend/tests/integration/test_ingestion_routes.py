import pytest
from unittest.mock import patch

pytestmark = pytest.mark.asyncio

async def test_trigger_ingestion_wrong_password(client):
    response = await client.post("/api/ingestion/trigger", json={"password": "wrong"})
    assert response.status_code == 401

async def test_trigger_ingestion_success(client):
    with patch("src.ingestion.router.run_ingestion"):
        with patch("src.ingestion.router.is_ingestion_running", return_value=False):
            response = await client.post("/api/ingestion/trigger", json={"password": "testpass"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "started" in data["message"]

async def test_trigger_ingestion_already_running(client):
    with patch("src.ingestion.router.is_ingestion_running", return_value=True):
        response = await client.post("/api/ingestion/trigger", json={"password": "testpass"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

async def test_ingestion_status(client):
    with patch("src.ingestion.router.is_ingestion_running", return_value=True):
        response = await client.get("/api/ingestion/status")
        assert response.status_code == 200
        assert response.json() == {"running": True}
