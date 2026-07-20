import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text


def test_ingest_game_squads_skips_when_no_game_info():
    """If get_game_info raises an exception, ingest_game_squads should silently skip."""
    from src.ingestion.game_stats import ingest_game_squads

    mock_session = MagicMock()
    with patch("src.ingestion.game_stats.get_game_info", side_effect=Exception("Not found")):
        # Should not raise — silently logs and returns
        ingest_game_squads(mock_session, game_id=1, game_external_id=999, team_id_map={})

    mock_session.commit.assert_not_called()


def test_ingest_game_squads_skips_empty_score_sheets():
    """If score sheets have no data, no rows should be inserted."""
    from src.ingestion.game_stats import ingest_game_squads

    mock_session = MagicMock()
    mock_game_info = {
        "home_score_sheet": {},
        "away_score_sheet": {},
    }
    with patch("src.ingestion.game_stats.get_game_info", return_value=mock_game_info):
        ingest_game_squads(mock_session, game_id=1, game_external_id=999, team_id_map={})

    mock_session.execute.assert_not_called()


def test_ingest_game_squads_inserts_players():
    """Given valid score sheet data, players should be inserted into game_squads."""
    from src.ingestion.game_stats import ingest_game_squads

    mock_session = MagicMock()
    # Simulate a score sheet with 2 players
    mock_game_info = {
        "home_score_sheet": {
            "id": "sheet-1",
            "team_id": 100,
        },
        "away_score_sheet": {},
    }
    mock_score_sheet = [
        {"member": {"id": 1, "name": "Player A"}, "team_id": 100, "player_number": 10, "position_id": 1},
        {"member": {"id": 2, "name": "Player B"}, "team_id": 100, "player_number": 11, "position_id": 2},
    ]
    team_id_map = {100: 50}  # external_id 100 → db_id 50

    with (
        patch("src.ingestion.game_stats.get_game_info", return_value=mock_game_info),
        patch("src.ingestion.game_stats.get_score_sheet", return_value=mock_score_sheet),
        patch("src.ingestion.game_stats.upsert_player", side_effect=[10, 20]),  # returns db player IDs
    ):
        ingest_game_squads(mock_session, game_id=1, game_external_id=999, team_id_map=team_id_map)

    # Should have called execute twice (once per player) + commit
    assert mock_session.execute.call_count == 2
    mock_session.commit.assert_called_once()


def test_ingest_game_squads_skips_unknown_team_ids():
    """Players with team IDs not in team_id_map should be skipped."""
    from src.ingestion.game_stats import ingest_game_squads

    mock_session = MagicMock()
    mock_game_info = {"home_score_sheet": {"id": "sheet-1", "team_id": 100}, "away_score_sheet": {}}
    mock_score_sheet = [
        {"member": {"id": 1, "name": "Player A"}, "team_id": 999, "player_number": 10, "position_id": 1},
    ]
    team_id_map = {100: 50}  # 999 is NOT in the map

    with (
        patch("src.ingestion.game_stats.get_game_info", return_value=mock_game_info),
        patch("src.ingestion.game_stats.get_score_sheet", return_value=mock_score_sheet),
        patch("src.ingestion.game_stats.upsert_player", return_value=10),
    ):
        ingest_game_squads(mock_session, game_id=1, game_external_id=999, team_id_map=team_id_map)

    mock_session.execute.assert_not_called()
