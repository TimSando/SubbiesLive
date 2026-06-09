import pytest
from tests.factories import make_club, make_competition, make_team

pytestmark = pytest.mark.asyncio

async def test_list_clubs_empty(client):
    response = await client.get("/api/clubs")
    assert response.status_code == 200
    assert response.json() == []

async def test_list_clubs_returns_seeded_data(client, db_session):
    await make_club(db_session, name="Mosman Whales", short_name="Mosman")
    response = await client.get("/api/clubs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Mosman Whales"

async def test_get_club_not_found(client):
    response = await client.get("/api/clubs/99999")
    assert response.status_code == 404

async def test_get_club_detail(client, db_session):
    club = await make_club(db_session, name="Colleagues", short_name="Colleagues")
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    await make_team(db_session, club_id=club.id, competition_id=comp.id, name="Colleagues 1st Grade", external_id=5001)

    response = await client.get(f"/api/clubs/{club.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Colleagues"
    assert len(data["teams"]) == 1
    assert data["teams"][0]["name"] == "Colleagues 1st Grade"
