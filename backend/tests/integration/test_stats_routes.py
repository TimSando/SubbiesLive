import pytest
from tests.factories import (
    make_player,
    make_club,
    make_competition,
    make_team,
    make_round,
    make_game,
    make_player_history,
)

pytestmark = pytest.mark.asyncio


async def test_player_stats_empty(client):
    response = await client.get("/api/stats/players")
    assert response.status_code == 200
    assert response.json() == []


async def test_club_stats_empty(client):
    response = await client.get("/api/stats/clubs")
    assert response.status_code == 200
    assert response.json() == []


async def test_overview_empty(client):
    response = await client.get("/api/stats/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tries"] == 0
    assert data["games_played"] == 0


async def test_stats_with_data(client, db_session):
    # Setup data
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r = await make_round(
        db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201
    )

    club1 = await make_club(db_session, name="Colleagues")
    club2 = await make_club(db_session, name="Mosman")

    team1 = await make_team(
        db_session,
        club_id=club1.id,
        competition_id=comp.id,
        name="Colleagues 1st",
        external_id=5001,
    )
    team2 = await make_team(
        db_session,
        club_id=club2.id,
        competition_id=comp.id,
        name="Mosman 1st",
        external_id=5002,
    )

    game = await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team1.id,
        away_team_id=team2.id,
        external_id=10001,
    )

    p = await make_player(db_session, name="Phil Waugh", external_id=1001)

    await make_player_history(
        db_session,
        player_id=p.id,
        game_id=game.id,
        team_id=team1.id,
        tries=2,
        conversions=1,
        points=12,
    )

    # 1. Test Player Stats
    response = await client.get(
        "/api/stats/players", params={"competition_id": comp.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["player_name"] == "Phil Waugh"
    assert data[0]["tries"] == 2
    assert data[0]["total_points"] == 12

    # 2. Test Club Stats
    response = await client.get("/api/stats/clubs", params={"competition_id": comp.id})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["club_name"] == "Colleagues"
    assert data[0]["tries"] == 2

    # 3. Test Season Overview
    response = await client.get(
        "/api/stats/overview", params={"competition_id": comp.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_tries"] == 2
    assert data["top_scorer_name"] == "Phil Waugh"

    # 4. Test Club Depth Stats
    response = await client.get(
        "/api/stats/clubs/depth", params={"competition_id": comp.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["club_name"] == "Colleagues"
    assert data[0]["total_players"] == 1

    # 5. Test Team Form Stats
    response = await client.get(f"/api/stats/team/{team1.id}/form")
    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] == team1.id
    assert data["games_played"] == 1
    assert data["total_tries"] == 2
