import pytest
from datetime import datetime
from tests.factories import (
    make_club,
    make_competition,
    make_team,
    make_round,
    make_game,
    make_player,
    make_player_history,
)

pytestmark = pytest.mark.asyncio


async def test_get_team_not_found(client):
    response = await client.get("/api/teams/99999")
    assert response.status_code == 404


async def test_get_team_detail(client, db_session):
    club = await make_club(db_session, name="Randwick Gallopers")
    club.logo_url = "http://example.com/logo.png"
    await db_session.flush()
    comp = await make_competition(db_session, name="Kentwell Cup", external_id=12)

    team = await make_team(
        db_session, club_id=club.id, competition_id=comp.id, name="Randwick 1st Grade"
    )

    response = await client.get(f"/api/teams/{team.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Randwick 1st Grade"
    assert data["club_name"] == "Randwick Gallopers"
    assert data["club_logo_url"] == "http://example.com/logo.png"
    assert data["competition_name"] == "Kentwell Cup"
    assert data["year"] == 2026
    assert data["stats"]["games_played"] == 0


async def test_get_team_detail_with_stats_by_competition_year(client, db_session):
    club_home = await make_club(db_session, name="Home Club")
    club_away = await make_club(db_session, name="Away Club")

    # Create a 2025 Competition and Team
    comp_2025 = await make_competition(
        db_session, name="Kentwell Cup 2025", external_id=15
    )
    comp_2025.year = 2025
    await db_session.flush()

    round_2025 = await make_round(db_session, competition_id=comp_2025.id)
    team_2025 = await make_team(
        db_session,
        club_id=club_home.id,
        competition_id=comp_2025.id,
        name="Home Team 2025",
        external_id=2001,
    )
    team_away_2025 = await make_team(
        db_session,
        club_id=club_away.id,
        competition_id=comp_2025.id,
        name="Away Team 2025",
        external_id=2002,
    )

    # 2025 Game: Home Team wins 25 - 10
    game_2025 = await make_game(
        db_session,
        round_id=round_2025.id,
        home_team_id=team_2025.id,
        away_team_id=team_away_2025.id,
        game_date=datetime(2025, 5, 10),
        home_score=25,
        away_score=10,
        status="completed",
        external_id=3001,
    )

    player = await make_player(db_session, name="Toby Sanders")
    await make_player_history(
        db_session,
        player_id=player.id,
        game_id=game_2025.id,
        team_id=team_2025.id,
        tries=2,
        conversions=3,
        yellow_cards=1,
        points=16,
    )

    # Fetch 2025 team stats (should automatically filter to 2025 since team is in a 2025 competition)
    response_2025 = await client.get(f"/api/teams/{team_2025.id}")
    assert response_2025.status_code == 200
    data_2025 = response_2025.json()
    assert data_2025["year"] == 2025
    assert data_2025["stats"]["games_played"] == 1
    assert data_2025["stats"]["wins"] == 1
    assert data_2025["stats"]["losses"] == 0
    assert data_2025["stats"]["points_for"] == 25
    assert data_2025["stats"]["points_against"] == 10
    assert data_2025["stats"]["total_tries"] == 2
    assert data_2025["stats"]["total_conversions"] == 3
    assert data_2025["stats"]["total_yellow_cards"] == 1
