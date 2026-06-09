from datetime import datetime
from src.refzone.matching import (
    clean_team_name,
    match_team_names,
    parse_rx_moment_to_sydney,
    match_competition_names,
    find_matching_game,
)


def test_clean_team_name():
    assert clean_team_name("Colleagues - Kentwell Cup") == "colleagues"
    assert clean_team_name("Mosman RUFC") == "mosman"
    assert clean_team_name("UNSW Rugby Club") == "unsw"
    assert clean_team_name("Sydney University Women's") == "sydney uni womens"
    assert clean_team_name(None) == ""


def test_match_team_names_exact():
    is_match, needs_review = match_team_names("Mosman", "Mosman RUFC")
    assert is_match
    assert not needs_review


def test_match_team_names_aliases():
    is_match, needs_review = match_team_names("UNSW", "University of New South Wales")
    assert is_match
    assert not needs_review


def test_match_team_names_overlap():
    # Length of "Hunters" (7) < 20 * 0.6 (12) -> should trigger needs_review
    is_match, needs_review = match_team_names("Hunters", "Hunters Hill A Grade")
    assert is_match
    assert needs_review


def test_match_team_names_no_match():
    is_match, _ = match_team_names("Colleagues", "Mosman")
    assert not is_match


def test_parse_rx_moment_to_sydney():
    # Unix timestamp in ms: 1717887600000 is 2024-06-08 23:00 UTC (09:00 AEST)
    dt = parse_rx_moment_to_sydney(1717887600000)
    assert dt is not None
    assert dt.hour == 9
    assert dt.minute == 0

    # Date string with UTC offset: 2024-06-09T07:00:00Z is 17:00 AEST
    dt2 = parse_rx_moment_to_sydney("2024-06-09T07:00:00Z")
    assert dt2 is not None
    assert dt2.hour == 17
    assert dt2.minute == 0


def test_match_competition_names():
    assert match_competition_names("Subbies Kentwell Cup", "Kentwell Cup")
    assert not match_competition_names("Subbies", "Shute Shield")


def test_find_matching_game():
    db_games = [
        {
            "id": 1,
            "game_date": datetime(2024, 6, 9, 15, 0),
            "home_team_name": "Colleagues RUFC",
            "away_team_name": "Mosman Whales",
        },
        {
            "id": 2,
            "game_date": datetime(2024, 6, 9, 15, 10),
            "home_team_name": "Barker Old Boys",
            "away_team_name": "Hunters Hill",
        },
    ]

    # Match Colleagues vs Mosman (time close enough, teams match)
    match_id = find_matching_game(
        app_moment=datetime(2024, 6, 9, 15, 5),
        app_home_team="Colleagues",
        app_away_team="Mosman",
        db_games=db_games,
    )
    assert match_id == 1

    # Time outside window (15:00 vs 16:30)
    match_id2 = find_matching_game(
        app_moment=datetime(2024, 6, 9, 16, 30),
        app_home_team="Colleagues",
        app_away_team="Mosman",
        db_games=db_games,
    )
    assert match_id2 is None
