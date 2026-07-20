import pytest
from datetime import datetime, timedelta
from tests.factories import (
    make_club,
    make_competition,
    make_round,
    make_team,
    make_game,
)
from src.ratings.models import TeamRatingHistory

pytestmark = pytest.mark.asyncio


async def test_prediction_returns_404_for_nonexistent_game(client):
    """GET /api/ratings/predictions/99999 should return 404."""
    response = await client.get("/api/ratings/predictions/99999")
    assert response.status_code == 404


async def test_prediction_returns_data_for_upcoming_game(client, db_session):
    """Prediction endpoint should return odds for a scheduled game with rated teams."""
    comp = await make_competition(db_session, name="Test Cup", external_id=900)
    r = await make_round(
        db_session, competition_id=comp.id, name="R1", number=1, external_id=9001
    )
    club1 = await make_club(db_session, name="Alpha FC")
    club2 = await make_club(db_session, name="Beta FC")
    team1 = await make_team(
        db_session,
        club_id=club1.id,
        competition_id=comp.id,
        name="Alpha 1st",
        external_id=9101,
    )
    team2 = await make_team(
        db_session,
        club_id=club2.id,
        competition_id=comp.id,
        name="Beta 1st",
        external_id=9102,
    )

    game_past = await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team1.id,
        away_team_id=team2.id,
        home_score=20,
        away_score=10,
        status="completed",
        external_id=9801,
    )

    # Seed rating history rows directly (simulating a backfill)
    db_session.add(
        TeamRatingHistory(
            team_id=team1.id,
            club_id=club1.id,
            game_id=game_past.id,
            rating_before=1500.0,
            rating_after=1550.0,
            opponent_team_id=team2.id,
            opponent_rating=1500.0,
            expected_result=0.5,
            actual_result=1.0,
        )
    )
    db_session.add(
        TeamRatingHistory(
            team_id=team2.id,
            club_id=club2.id,
            game_id=game_past.id,
            rating_before=1500.0,
            rating_after=1450.0,
            opponent_team_id=team1.id,
            opponent_rating=1500.0,
            expected_result=0.5,
            actual_result=0.0,
        )
    )
    await db_session.flush()

    # Create upcoming game
    upcoming_game = await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team1.id,
        away_team_id=team2.id,
        home_score=None,
        away_score=None,
        status="scheduled",
        external_id=9201,
        game_date=datetime.now() + timedelta(days=7),
    )

    response = await client.get(f"/api/ratings/predictions/{upcoming_game.id}")
    assert response.status_code == 200
    data = response.json()

    # Verify response shape
    assert "home_win_probability" in data
    assert "away_win_probability" in data
    assert "draw_probability" in data
    assert "home_odds_display" in data
    assert "away_odds_display" in data

    # Probabilities should sum to ~1.0
    total = (
        data["home_win_probability"]
        + data["away_win_probability"]
        + data["draw_probability"]
    )
    assert abs(total - 1.0) < 0.02

    # Team1 is rated higher (1550 vs 1450), so should be favoured
    assert data["home_win_probability"] > data["away_win_probability"]


async def test_prediction_returns_default_for_unrated_teams(client, db_session):
    """If teams have no rating history, prediction should return default even odds."""
    comp = await make_competition(db_session, name="New Cup", external_id=950)
    r = await make_round(
        db_session, competition_id=comp.id, name="R1", number=1, external_id=9501
    )
    club1 = await make_club(db_session, name="New Club A")
    club2 = await make_club(db_session, name="New Club B")
    team1 = await make_team(
        db_session,
        club_id=club1.id,
        competition_id=comp.id,
        name="New A 1st",
        external_id=9601,
    )
    team2 = await make_team(
        db_session,
        club_id=club2.id,
        competition_id=comp.id,
        name="New B 1st",
        external_id=9602,
    )
    game = await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team1.id,
        away_team_id=team2.id,
        home_score=None,
        away_score=None,
        status="scheduled",
        external_id=9701,
        game_date=datetime.now() + timedelta(days=7),
    )

    response = await client.get(f"/api/ratings/predictions/{game.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["home_win_probability"] > data["away_win_probability"]
    # Check that they match expected values given home advantage
    assert abs(data["home_win_probability"] - 0.54) < 0.01


async def test_rating_history_returns_entries(client, db_session):
    """GET /api/ratings/history/{team_id} should return historical rating entries."""
    comp = await make_competition(db_session, name="History Cup", external_id=960)
    r = await make_round(
        db_session, competition_id=comp.id, name="R1", number=1, external_id=9601
    )
    club = await make_club(db_session, name="History FC")
    team = await make_team(
        db_session,
        club_id=club.id,
        competition_id=comp.id,
        name="History 1st",
        external_id=9701,
    )
    other_club = await make_club(db_session, name="Opponent FC")
    other_team = await make_team(
        db_session,
        club_id=other_club.id,
        competition_id=comp.id,
        name="Opponent 1st",
        external_id=9702,
    )

    game = await make_game(
        db_session,
        round_id=r.id,
        home_team_id=team.id,
        away_team_id=other_team.id,
        home_score=20,
        away_score=10,
        status="completed",
        external_id=9801,
    )

    db_session.add(
        TeamRatingHistory(
            team_id=team.id,
            club_id=club.id,
            game_id=game.id,
            rating_before=1500.0,
            rating_after=1520.0,
            opponent_team_id=other_team.id,
            opponent_rating=1500.0,
            expected_result=0.5,
            actual_result=1.0,
        )
    )
    await db_session.flush()

    response = await client.get(f"/api/ratings/history/{team.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["rating_before"] == 1500.0
    assert data[0]["rating_after"] == 1520.0
