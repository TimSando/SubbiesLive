from datetime import datetime
from src.competitions.models import Competition, Round, CompetitionMapping
from src.clubs.models import Club, Team
from src.games.models import Game, GameEvent, PlayerHistory
from src.players.models import Player


async def make_competition_mapping(
    db, *, name="Test Comp Mapping", division=None, grade=None
):
    mapping = CompetitionMapping(name=name, division=division, grade=grade)
    db.add(mapping)
    await db.flush()
    return mapping


async def make_competition(
    db, *, name="Test Competition", external_id=101, competition_mapping_id=None
):
    comp = Competition(
        name=name,
        external_id=external_id,
        competition_mapping_id=competition_mapping_id,
    )
    db.add(comp)
    await db.flush()
    return comp


async def make_round(db, *, competition_id, name="Round 1", number=1, external_id=201):
    r = Round(
        competition_id=competition_id, name=name, number=number, external_id=external_id
    )
    db.add(r)
    await db.flush()
    return r


async def make_club(db, *, name="Test Club", short_name="TC", has_womens_team=False):
    club = Club(name=name, short_name=short_name, has_womens_team=has_womens_team)
    db.add(club)
    await db.flush()
    return club


async def make_team(db, *, club_id, competition_id, name="Test Team", external_id=301):
    team = Team(
        club_id=club_id,
        competition_id=competition_id,
        name=name,
        external_id=external_id,
    )
    db.add(team)
    await db.flush()
    return team


async def make_game(
    db,
    *,
    round_id,
    home_team_id,
    away_team_id,
    game_date=None,
    location="Ground 1",
    home_score=20,
    away_score=15,
    status="completed",
    external_id=401,
):
    if game_date is None:
        game_date = datetime.now()
    game = Game(
        round_id=round_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        game_date=game_date,
        location=location,
        home_score=home_score,
        away_score=away_score,
        status=status,
        external_id=external_id,
    )
    db.add(game)
    await db.flush()
    return game


async def make_player(db, *, name="John Doe", external_id=501):
    player = Player(name=name, external_id=external_id)
    db.add(player)
    await db.flush()
    return player


async def make_game_event(
    db,
    *,
    game_id,
    team_id,
    player_id=None,
    event_type="try",
    points=5,
    player_number=14,
):
    event = GameEvent(
        game_id=game_id,
        team_id=team_id,
        player_id=player_id,
        event_type=event_type,
        points=points,
        player_number=player_number,
    )
    db.add(event)
    await db.flush()
    return event


async def make_player_history(
    db, *, player_id, game_id, team_id, tries=0, conversions=0, yellow_cards=0, points=0
):
    hist = PlayerHistory(
        player_id=player_id,
        game_id=game_id,
        team_id=team_id,
        tries=tries,
        conversions=conversions,
        yellow_cards=yellow_cards,
        points=points,
    )
    db.add(hist)
    await db.flush()
    return hist


async def make_game_squad(
    db, *, game_id, team_id, player_id, player_number=None, position_id=None
):
    from src.ratings.models import GameSquad
    squad = GameSquad(
        game_id=game_id,
        team_id=team_id,
        player_id=player_id,
        player_number=player_number,
        position_id=position_id,
    )
    db.add(squad)
    await db.flush()
    return squad


async def make_player_impact_score(
    db,
    *,
    player_id,
    team_id,
    club_id,
    competition_mapping_id=None,
    year=None,
    impact_score=0.0,
    games_with=0,
    games_without=0,
    win_rate_with=None,
    win_rate_without=None,
    margin_diff=None,
    confidence="low",
):
    from src.ratings.models import PlayerImpactScore
    score = PlayerImpactScore(
        player_id=player_id,
        team_id=team_id,
        club_id=club_id,
        competition_mapping_id=competition_mapping_id,
        year=year,
        impact_score=impact_score,
        games_with=games_with,
        games_without=games_without,
        win_rate_with=win_rate_with,
        win_rate_without=win_rate_without,
        margin_diff=margin_diff,
        confidence=confidence,
    )
    db.add(score)
    await db.flush()
    return score
