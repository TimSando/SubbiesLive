import pytest
import threading
from unittest.mock import MagicMock
from src.notifications.service import notify_game_update


@pytest.fixture
def mock_game_row():
    row = MagicMock()
    row.id = 123
    row.home_score = 14
    row.away_score = 12
    row.competition_id = 3
    row.competition_name = "Kentwell Cup"
    row.home_club_id = 1
    row.away_club_id = 2

    row.home_club_short_name = "Mosman"
    row.home_club_name = "Mosman Rugby Club"
    row.home_team_name = "Mosman"

    row.away_club_short_name = None
    row.away_club_name = "Colleagues"
    row.away_team_name = "Colleagues"

    row.parent_competition = "Kentwell Cup"
    row.division = "1st Grade"
    return row


@pytest.fixture
def mock_session(mock_game_row):
    session = MagicMock()

    def mock_execute(query, params=None):
        query_str = str(query)
        result = MagicMock()
        if "FROM games" in query_str:
            result.fetchone.return_value = mock_game_row
        elif "FROM pwa_subscriptions" in query_str:
            sub = {
                "endpoint": "https://example.com/push",
                "p256dh": "p256dh_val",
                "auth": "auth_val",
            }
            result.mappings.return_value = [sub]
        return result

    session.execute.side_effect = mock_execute
    return session


def test_notification_formatting_full_event(mocker, mock_session):
    """Test formatting when a specific club and detail message (e.g. Try scorer) is provided."""
    mocker.patch("threading.Thread")

    notify_game_update(
        session=mock_session,
        game_id=123,
        update_type="Try",
        detail_message="(J. Smith)",
        event_club_name="Mosman",
    )

    # Assert thread was spawned with the expected smartwatch-optimized payload
    assert threading.Thread.call_count == 1
    args, kwargs = threading.Thread.call_args
    payload = kwargs["args"][2]

    assert payload == {
        "title": "Mosman 14 - 12 Colleagues",
        "body": "Kentwell Cup • Mosman Try (J. Smith)",
        "url": "/games/123",
        "tag": "game-123",
    }


def test_notification_formatting_no_detail(mocker, mock_session):
    """Test formatting for a card or generic event where no specific detail message exists."""
    mocker.patch("threading.Thread")

    notify_game_update(
        session=mock_session,
        game_id=123,
        update_type="Yellow Card",
        detail_message="",
        event_club_name="Colleagues",
    )

    assert threading.Thread.call_count == 1
    args, kwargs = threading.Thread.call_args
    payload = kwargs["args"][2]

    assert payload == {
        "title": "Mosman 14 - 12 Colleagues",
        "body": "Kentwell Cup • Colleagues Yellow Card",
        "url": "/games/123",
        "tag": "game-123",
    }


def test_notification_formatting_general_match_update(mocker, mock_session):
    """Test formatting for a general match update like Full Time, where no specific club is responsible."""
    mocker.patch("threading.Thread")

    notify_game_update(
        session=mock_session,
        game_id=123,
        update_type="Full Time",
        detail_message="",
        event_club_name="",
    )

    assert threading.Thread.call_count == 1
    args, kwargs = threading.Thread.call_args
    payload = kwargs["args"][2]

    assert payload == {
        "title": "Mosman 14 - 12 Colleagues",
        "body": "Kentwell Cup • Full Time",
        "url": "/games/123",
        "tag": "game-123",
    }
