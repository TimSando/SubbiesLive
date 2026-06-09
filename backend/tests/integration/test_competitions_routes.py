import pytest
from tests.factories import make_competition, make_round

pytestmark = pytest.mark.asyncio


async def test_list_competitions_empty(client):
    response = await client.get("/api/competitions")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_competitions_returns_seeded_data(client, db_session):
    await make_competition(db_session, name="Shute Shield", external_id=42)
    response = await client.get("/api/competitions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Shute Shield"


async def test_get_competition_not_found(client):
    response = await client.get("/api/competitions/99999")
    assert response.status_code == 404


async def test_get_competition_with_rounds(client, db_session):
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    await make_round(
        db_session, competition_id=comp.id, name="Round 1", number=1, external_id=200
    )

    response = await client.get(f"/api/competitions/{comp.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Kentwell Cup"
    assert len(body["rounds"]) == 1
    assert body["rounds"][0]["name"] == "Round 1"
