import pytest
from tests.factories import (
    make_club, make_competition, make_round, make_team,
    make_game, make_player, make_player_history,
)

pytestmark = pytest.mark.asyncio


async def test_player_impact_returns_404_for_nonexistent_team(client):
    """GET /api/ratings/player-impact/99999 should return 404."""
    response = await client.get("/api/ratings/player-impact/99999")
    assert response.status_code == 404


async def test_player_impact_returns_empty_for_unrated_team(client, db_session):
    """A team with no impact scores should return an empty players list."""
    comp = await make_competition(db_session, name="Impact Cup", external_id=800)
    club = await make_club(db_session, name="Impact FC")
    team = await make_team(db_session, club_id=club.id, competition_id=comp.id, name="Impact 1st", external_id=8001)

    response = await client.get(f"/api/ratings/player-impact/{team.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] == team.id
    assert data["players"] == []


async def test_player_impact_returns_ranked_players(client, db_session):
    """With seeded impact scores, endpoint should return players ranked by impact."""
    comp = await make_competition(db_session, name="Ranked Cup", external_id=810)
    club = await make_club(db_session, name="Ranked FC")
    team = await make_team(db_session, club_id=club.id, competition_id=comp.id, name="Ranked 1st", external_id=8101)

    # Seed player impact scores directly
    from src.ratings.models import PlayerImpactScore
    p1 = await make_player(db_session, name="Star Player", external_id=8201)
    p2 = await make_player(db_session, name="Avg Player", external_id=8202)

    db_session.add(PlayerImpactScore(
        player_id=p1.id, team_id=team.id, club_id=club.id,
        year=None,  # all-time
        impact_score=35.0, games_with=30, games_without=15,
        win_rate_with=0.8, win_rate_without=0.5,
        confidence="high",
    ))
    db_session.add(PlayerImpactScore(
        player_id=p2.id, team_id=team.id, club_id=club.id,
        year=None,
        impact_score=10.0, games_with=20, games_without=10,
        win_rate_with=0.55, win_rate_without=0.5,
        confidence="medium",
    ))
    await db_session.flush()

    response = await client.get(f"/api/ratings/player-impact/{team.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["players"]) == 2
    # Star Player should be ranked first
    assert data["players"][0]["player_name"] == "Star Player"
    assert data["players"][0]["impact_score"] == 35.0
    assert data["players"][1]["player_name"] == "Avg Player"


async def test_player_impact_filters_by_year(client, db_session):
    """Passing ?year=2025 should only return scores for that season."""
    comp = await make_competition(db_session, name="Year Cup", external_id=820)
    club = await make_club(db_session, name="Year FC")
    team = await make_team(db_session, club_id=club.id, competition_id=comp.id, name="Year 1st", external_id=8301)
    player = await make_player(db_session, name="Multi-Year Player", external_id=8401)

    from src.ratings.models import PlayerImpactScore
    # All-time score
    db_session.add(PlayerImpactScore(
        player_id=player.id, team_id=team.id, club_id=club.id,
        year=None, impact_score=25.0, games_with=40, games_without=20,
        confidence="high",
    ))
    # 2025 score
    db_session.add(PlayerImpactScore(
        player_id=player.id, team_id=team.id, club_id=club.id,
        year=2025, impact_score=32.0, games_with=12, games_without=6,
        confidence="medium",
    ))
    # 2024 score
    db_session.add(PlayerImpactScore(
        player_id=player.id, team_id=team.id, club_id=club.id,
        year=2024, impact_score=18.0, games_with=14, games_without=8,
        confidence="medium",
    ))
    await db_session.flush()

    # Query for 2025 season
    response = await client.get(f"/api/ratings/player-impact/{team.id}?year=2025")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2025
    assert len(data["players"]) == 1
    assert data["players"][0]["impact_score"] == 32.0

    # Query for career (no year param or year=null)
    response_career = await client.get(f"/api/ratings/player-impact/{team.id}")
    data_career = response_career.json()
    assert len(data_career["players"]) == 1
    assert data_career["players"][0]["impact_score"] == 25.0

    # Available years should include both 2024 and 2025
    assert 2024 in data_career["available_years"]
    assert 2025 in data_career["available_years"]
