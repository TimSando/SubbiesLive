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


async def test_rescheduled_rounds_logic(client, db_session):
    from datetime import datetime
    from tests.factories import (
        make_competition,
        make_round,
        make_club,
        make_team,
        make_game,
    )

    comp = await make_competition(db_session, name="Kentwell Cup", external_id=7)
    r1 = await make_round(
        db_session, competition_id=comp.id, name="Round 1", number=1, external_id=200
    )
    r2 = await make_round(
        db_session, competition_id=comp.id, name="Round 2", number=2, external_id=201
    )

    club_a = await make_club(db_session, name="Club A")
    club_b = await make_club(db_session, name="Club B")
    team_a = await make_team(
        db_session,
        club_id=club_a.id,
        competition_id=comp.id,
        name="Team A",
        external_id=300,
    )
    team_b = await make_team(
        db_session,
        club_id=club_b.id,
        competition_id=comp.id,
        name="Team B",
        external_id=301,
    )

    # Round 1 played on May 16th (normal)
    await make_game(
        db_session,
        round_id=r1.id,
        home_team_id=team_a.id,
        away_team_id=team_b.id,
        game_date=datetime(2026, 5, 16, 15, 0),
        external_id=400,
    )

    # Round 2 scheduled for May 23rd, but rescheduled to July 4th!
    # In database, the game has date July 4th
    await make_game(
        db_session,
        round_id=r2.id,
        home_team_id=team_a.id,
        away_team_id=team_b.id,
        game_date=datetime(2026, 7, 4, 15, 0),
        external_id=401,
    )

    # 1. Fetch competition by ID
    response = await client.get(f"/api/competitions/{comp.id}")
    assert response.status_code == 200
    body = response.json()

    # The rounds list should contain:
    # - Round 1 (May 16)
    # - Round 2 original empty slot (May 23)
    # - Round 2 rescheduled slot (July 4)
    rounds = body["rounds"]
    assert len(rounds) == 3

    assert rounds[0]["name"] == "Round 1"
    assert rounds[0]["is_rescheduled_empty"] is False

    assert rounds[1]["name"] == "Round 2"
    assert rounds[1]["is_rescheduled_empty"] is True
    assert rounds[1]["game_count"] == 0

    assert rounds[2]["name"] == "Round 2 (Resched)"
    assert rounds[2]["is_rescheduled_empty"] is False
    assert rounds[2]["game_count"] == 1
    assert rounds[2]["date_filter"] == "2026-07-04"

    # 2. Fetch games filtered by date
    # Test filtering with date_filter
    res_games = await client.get(f"/api/games?round_id={r2.id}&game_date=2026-07-04")
    assert res_games.status_code == 200
    games_data = res_games.json()
    assert len(games_data) == 1

    # Test filtering with another date (empty)
    res_games_empty = await client.get(
        f"/api/games?round_id={r2.id}&game_date=2026-05-23"
    )
    assert res_games_empty.status_code == 200
    assert len(res_games_empty.json()) == 0
