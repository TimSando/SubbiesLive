import pytest
from tests.factories import make_club, make_competition, make_round, make_team, make_game

pytestmark = pytest.mark.asyncio

async def test_list_games_empty(client):
    response = await client.get("/api/games")
    assert response.status_code == 200
    assert response.json() == []

async def test_list_games_returns_data(client, db_session):
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r = await make_round(db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201)
    club1 = await make_club(db_session, name="Colleagues")
    club2 = await make_club(db_session, name="Mosman")
    team1 = await make_team(db_session, club_id=club1.id, competition_id=comp.id, name="Colleagues 1st", external_id=5001)
    team2 = await make_team(db_session, club_id=club2.id, competition_id=comp.id, name="Mosman 1st", external_id=5002)
    
    game = await make_game(db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id, external_id=10001)

    response = await client.get("/api/games")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["external_id"] == 10001

async def test_list_live_games(client, db_session):
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r = await make_round(db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201)
    club1 = await make_club(db_session, name="Colleagues")
    club2 = await make_club(db_session, name="Mosman")
    team1 = await make_team(db_session, club_id=club1.id, competition_id=comp.id, name="Colleagues 1st", external_id=5001)
    team2 = await make_team(db_session, club_id=club2.id, competition_id=comp.id, name="Mosman 1st", external_id=5002)
    
    await make_game(db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id, status="in_progress", external_id=10002)
    await make_game(db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id, status="completed", external_id=10003)

    response = await client.get("/api/games/live")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "in_progress"

async def test_get_game_not_found(client):
    response = await client.get("/api/games/99999")
    assert response.status_code == 404

async def test_get_game_detail(client, db_session):
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r = await make_round(db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201)
    club1 = await make_club(db_session, name="Colleagues")
    club2 = await make_club(db_session, name="Mosman")
    team1 = await make_team(db_session, club_id=club1.id, competition_id=comp.id, name="Colleagues 1st", external_id=5001)
    team2 = await make_team(db_session, club_id=club2.id, competition_id=comp.id, name="Mosman 1st", external_id=5002)
    
    game = await make_game(db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id, external_id=10004)

    response = await client.get(f"/api/games/{game.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == game.id
    assert "events" in data
