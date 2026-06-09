import pytest
from tests.factories import make_player, make_club, make_competition, make_team, make_round, make_game, make_player_history

pytestmark = pytest.mark.asyncio

async def test_list_players_empty(client):
    response = await client.get("/api/players")
    assert response.status_code == 200
    assert response.json() == []

async def test_list_players_search_and_pagination(client, db_session):
    p1 = await make_player(db_session, name="David Campese", external_id=1001)
    p2 = await make_player(db_session, name="Michael Lynagh", external_id=1002)

    response = await client.get("/api/players", params={"search": "David"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "David Campese"

async def test_get_player_not_found(client):
    response = await client.get("/api/players/99999")
    assert response.status_code == 404

async def test_get_player_detail(client, db_session):
    p = await make_player(db_session, name="George Gregan", external_id=1003)
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r = await make_round(db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201)
    club1 = await make_club(db_session, name="Colleagues")
    club2 = await make_club(db_session, name="Mosman")
    team1 = await make_team(db_session, club_id=club1.id, competition_id=comp.id, name="Colleagues 1st", external_id=5001)
    team2 = await make_team(db_session, club_id=club2.id, competition_id=comp.id, name="Mosman 1st", external_id=5002)
    game = await make_game(db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id, external_id=10001)
    
    await make_player_history(
        db_session, player_id=p.id, game_id=game.id, team_id=team1.id,
        tries=2, conversions=1, points=12
    )

    response = await client.get(f"/api/players/{p.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "George Gregan"
    assert "stats" in data
    assert data["stats"]["total_tries"] == 2
    assert data["stats"]["total_points"] == 12
    assert len(data["teams"]) == 1
    assert data["teams"][0]["team_name"] == "Colleagues 1st"
