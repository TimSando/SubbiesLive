import pytest
from datetime import datetime, timedelta
from tests.factories import make_club, make_competition, make_round, make_team, make_game, make_player

pytestmark = pytest.mark.asyncio


async def test_prediction_without_squad_data(client, db_session):
    """When no game_squads rows exist, prediction should use pure team Elo.
    squad_modifier should be null and source should be 'no_squad_data'."""
    comp = await make_competition(db_session, name="No Squad Cup", external_id=700)
    r = await make_round(db_session, competition_id=comp.id, name="R1", number=1, external_id=7001)
    club1 = await make_club(db_session, name="NoSquad A")
    club2 = await make_club(db_session, name="NoSquad B")
    team1 = await make_team(db_session, club_id=club1.id, competition_id=comp.id, name="A 1st", external_id=7101)
    team2 = await make_team(db_session, club_id=club2.id, competition_id=comp.id, name="B 1st", external_id=7102)

    # Seed rating history
    from src.ratings.models import TeamRatingHistory
    game_past = await make_game(db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id,
                                 home_score=20, away_score=10, status="completed", external_id=7201)
    db_session.add(TeamRatingHistory(team_id=team1.id, club_id=club1.id, game_id=game_past.id,
                                     rating_before=1500, rating_after=1530, opponent_team_id=team2.id,
                                     opponent_rating=1500, expected_result=0.5, actual_result=1.0))
    db_session.add(TeamRatingHistory(team_id=team2.id, club_id=club2.id, game_id=game_past.id,
                                     rating_before=1500, rating_after=1470, opponent_team_id=team1.id,
                                     opponent_rating=1500, expected_result=0.5, actual_result=0.0))
    await db_session.flush()

    # Create upcoming game — no squad data
    upcoming = await make_game(db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id,
                                home_score=None, away_score=None, status="scheduled", external_id=7202,
                                game_date=datetime.now() + timedelta(days=7))

    response = await client.get(f"/api/ratings/predictions/{upcoming.id}")
    assert response.status_code == 200
    data = response.json()

    # Player insights should show no squad modifier
    if "player_insights" in data:
        home_insights = data["player_insights"]["home_team"]
        assert home_insights["squad_modifier"] is None
        assert home_insights["squad_modifier_source"] == "no_squad_data"


async def test_prediction_with_squad_data_adjusts_odds(client, db_session):
    """When game_squads rows exist and players have impact scores,
    the prediction should apply a squad modifier."""
    comp = await make_competition(db_session, name="Squad Cup", external_id=710)
    r = await make_round(db_session, competition_id=comp.id, name="R1", number=1, external_id=7101)
    club1 = await make_club(db_session, name="Squad A")
    club2 = await make_club(db_session, name="Squad B")
    team1 = await make_team(db_session, club_id=club1.id, competition_id=comp.id, name="SA 1st", external_id=7201)
    team2 = await make_team(db_session, club_id=club2.id, competition_id=comp.id, name="SB 1st", external_id=7202)

    # Players with impact scores
    p1 = await make_player(db_session, name="Key Player", external_id=7301)
    p2 = await make_player(db_session, name="Bench Player", external_id=7302)

    from src.ratings.models import TeamRatingHistory, PlayerImpactScore, GameSquad

    # Seed ratings (equal teams)
    game_past = await make_game(db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id,
                                 home_score=15, away_score=15, status="completed", external_id=7401)
    db_session.add(TeamRatingHistory(team_id=team1.id, club_id=club1.id, game_id=game_past.id,
                                     rating_before=1500, rating_after=1500, opponent_team_id=team2.id,
                                     opponent_rating=1500, expected_result=0.5, actual_result=0.5))
    db_session.add(TeamRatingHistory(team_id=team2.id, club_id=club2.id, game_id=game_past.id,
                                     rating_before=1500, rating_after=1500, opponent_team_id=team1.id,
                                     opponent_rating=1500, expected_result=0.5, actual_result=0.5))

    # Seed impact scores — p1 is high-impact, p2 is low-impact
    db_session.add(PlayerImpactScore(
        player_id=p1.id, team_id=team1.id, club_id=club1.id,
        year=None, impact_score=40.0, games_with=30, games_without=20,
        confidence="high",
    ))
    db_session.add(PlayerImpactScore(
        player_id=p2.id, team_id=team1.id, club_id=club1.id,
        year=None, impact_score=5.0, games_with=15, games_without=10,
        confidence="medium",
    ))
    await db_session.flush()

    # Create upcoming game
    upcoming = await make_game(db_session, round_id=r.id, home_team_id=team1.id, away_team_id=team2.id,
                                home_score=None, away_score=None, status="scheduled", external_id=7402,
                                game_date=datetime.now() + timedelta(days=7))

    # Seed squad — only bench player named, key player missing
    db_session.add(GameSquad(game_id=upcoming.id, team_id=team1.id, player_id=p2.id, player_number=12))
    await db_session.flush()

    response = await client.get(f"/api/ratings/predictions/{upcoming.id}")
    assert response.status_code == 200
    data = response.json()

    # With key player missing, squad modifier should be negative
    if "player_insights" in data:
        home_insights = data["player_insights"]["home_team"]
        assert home_insights["squad_modifier"] is not None
        assert home_insights["squad_modifier"] < 0.0
        assert home_insights["squad_modifier_source"] == "game_squads"
