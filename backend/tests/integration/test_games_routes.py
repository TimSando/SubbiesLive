import pytest
from tests.factories import (
    make_club,
    make_competition,
    make_round,
    make_team,
    make_game,
)

pytestmark = pytest.mark.asyncio


async def test_list_games_empty(client):
    response = await client.get("/api/games")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_games_returns_data(client, db_session):
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

    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team1.id,
        away_team_id=team2.id,
        external_id=10001,
    )

    response = await client.get("/api/games")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["external_id"] == 10001


async def test_list_live_games(client, db_session):
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

    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team1.id,
        away_team_id=team2.id,
        status="in_progress",
        external_id=10002,
    )
    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team1.id,
        away_team_id=team2.id,
        status="completed",
        external_id=10003,
    )

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
        external_id=10004,
    )

    response = await client.get(f"/api/games/{game.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == game.id
    assert "events" in data


async def test_list_games_filter_by_club_id_home(client, db_session):
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r = await make_round(
        db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201
    )
    club_a = await make_club(db_session, name="Colleagues")
    club_b = await make_club(db_session, name="Mosman")

    team_a = await make_team(
        db_session,
        club_id=club_a.id,
        competition_id=comp.id,
        name="Colleagues 1st",
        external_id=5001,
    )
    team_b = await make_team(
        db_session,
        club_id=club_b.id,
        competition_id=comp.id,
        name="Mosman 1st",
        external_id=5002,
    )

    # Game with club_a as home team
    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team_a.id,
        away_team_id=team_b.id,
        external_id=10005,
    )
    # Game with club_b only (not club_a)
    club_c = await make_club(db_session, name="Waverley")
    team_c = await make_team(
        db_session,
        club_id=club_c.id,
        competition_id=comp.id,
        name="Waverley 1st",
        external_id=5003,
    )
    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team_b.id,
        away_team_id=team_c.id,
        external_id=10006,
    )

    response = await client.get(f"/api/games?club_id={club_a.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["external_id"] == 10005


async def test_list_games_filter_by_club_id_away(client, db_session):
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r = await make_round(
        db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201
    )
    club_a = await make_club(db_session, name="Colleagues")
    club_b = await make_club(db_session, name="Mosman")

    team_a = await make_team(
        db_session,
        club_id=club_a.id,
        competition_id=comp.id,
        name="Colleagues 1st",
        external_id=5001,
    )
    team_b = await make_team(
        db_session,
        club_id=club_b.id,
        competition_id=comp.id,
        name="Mosman 1st",
        external_id=5002,
    )

    # Game with club_a as away team (club_b home)
    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team_b.id,
        away_team_id=team_a.id,
        external_id=10007,
    )

    response = await client.get(f"/api/games?club_id={club_a.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["external_id"] == 10007


async def test_list_games_club_id_with_status_filter(client, db_session):
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r = await make_round(
        db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201
    )
    club_a = await make_club(db_session, name="Colleagues")
    club_b = await make_club(db_session, name="Mosman")

    team_a = await make_team(
        db_session,
        club_id=club_a.id,
        competition_id=comp.id,
        name="Colleagues 1st",
        external_id=5001,
    )
    team_b = await make_team(
        db_session,
        club_id=club_b.id,
        competition_id=comp.id,
        name="Mosman 1st",
        external_id=5002,
    )

    # Completed game
    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team_a.id,
        away_team_id=team_b.id,
        status="completed",
        external_id=10008,
    )
    from datetime import datetime, timedelta

    # Scheduled game
    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team_a.id,
        away_team_id=team_b.id,
        status="scheduled",
        game_date=datetime.now() + timedelta(days=1),
        external_id=10009,
    )

    response = await client.get(f"/api/games?club_id={club_a.id}&status=completed")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["external_id"] == 10008
    assert data[0]["status"] == "completed"


async def test_list_games_club_id_no_results(client, db_session):
    response = await client.get("/api/games?club_id=99999")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_games_without_club_id_unchanged(client, db_session):
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r = await make_round(
        db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201
    )
    club_a = await make_club(db_session, name="Colleagues")
    club_b = await make_club(db_session, name="Mosman")

    team_a = await make_team(
        db_session,
        club_id=club_a.id,
        competition_id=comp.id,
        name="Colleagues 1st",
        external_id=5001,
    )
    team_b = await make_team(
        db_session,
        club_id=club_b.id,
        competition_id=comp.id,
        name="Mosman 1st",
        external_id=5002,
    )

    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team_a.id,
        away_team_id=team_b.id,
        external_id=10010,
    )
    await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team_b.id,
        away_team_id=team_a.id,
        external_id=10011,
    )

    response = await client.get("/api/games")
    assert response.status_code == 200
    data = response.json()
    # Should return at least 2 games
    assert len(data) >= 2
