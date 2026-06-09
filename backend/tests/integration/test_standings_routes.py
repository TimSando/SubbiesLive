import pytest
from tests.factories import make_club, make_competition, make_round, make_team, make_game

pytestmark = pytest.mark.asyncio

async def test_get_standings_not_found(client):
    response = await client.get("/api/standings/99999")
    assert response.status_code == 404

async def test_get_standings_empty_comp(client, db_session):
    comp = await make_competition(db_session, name="Empty Comp", external_id=99)
    response = await client.get(f"/api/standings/{comp.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["competition_id"] == comp.id
    assert data["standings"] == []

async def test_get_standings_calculates_ladder(client, db_session):
    comp = await make_competition(db_session, name="Subbies Cup", external_id=10)
    r = await make_round(db_session, competition_id=comp.id, name="Round 1", number=1, external_id=201)
    
    club1 = await make_club(db_session, name="Hunters Hill")
    club2 = await make_club(db_session, name="Barker Old Boys")
    
    team1 = await make_team(db_session, club_id=club1.id, competition_id=comp.id, name="Hunters Hill 1st", external_id=5001)
    team2 = await make_team(db_session, club_id=club2.id, competition_id=comp.id, name="Barker 1st", external_id=5002)
    
    # Hunters Hill beats Barker 25-10
    await make_game(
        db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id,
        home_score=25, away_score=10, status="completed", external_id=10001
    )

    response = await client.get(f"/api/standings/{comp.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["competition_id"] == comp.id
    
    standings = data["standings"]
    assert len(standings) == 2
    
    # Hunters Hill should be 1st
    assert standings[0]["team_id"] == team1.id
    assert standings[0]["position"] == 1
    assert standings[0]["won"] == 1
    assert standings[0]["competition_points"] == 4
    
    # Barker should be 2nd
    assert standings[1]["team_id"] == team2.id
    assert standings[1]["position"] == 2
    assert standings[1]["lost"] == 1
    assert standings[1]["competition_points"] == 0
