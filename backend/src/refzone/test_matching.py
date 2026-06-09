import unittest
from datetime import datetime
from src.refzone.matching import (
    clean_team_name,
    match_team_names,
    parse_rx_moment_to_sydney,
    find_matching_game
)

class TestRefZoneMatching(unittest.TestCase):
    def test_clean_team_name(self):
        self.assertEqual(clean_team_name("Colleagues - Kentwell Cup"), "colleagues")
        self.assertEqual(clean_team_name("Mosman RUFC"), "mosman")
        self.assertEqual(clean_team_name("Sydney University RFC"), "sydney uni")
        self.assertEqual(clean_team_name("UNSW Women's"), "unsw womens")
        self.assertEqual(clean_team_name("Two Blues RUFC"), "two blues")

    def test_match_team_names(self):
        # Exact match after cleaning
        matched, review = match_team_names("Colleagues - Kentwell Cup", "Colleagues RUFC")
        self.assertTrue(matched)
        self.assertFalse(review)

        # Alias match
        matched, review = match_team_names("UNSW", "University of New South Wales")
        self.assertTrue(matched)
        self.assertFalse(review)

        # Substring match
        matched, review = match_team_names("Western Sydney Two Blues", "Two Blues")
        self.assertTrue(matched)
        
        # Non-matching
        matched, review = match_team_names("Colleagues", "Mosman")
        self.assertFalse(matched)

    def test_parse_rx_moment_to_sydney(self):
        # 1682399700000 -> 2023-04-25 05:15:00 UTC -> 2023-04-25 15:15:00 Sydney (AEST is UTC+10)
        dt = parse_rx_moment_to_sydney(1682399700000)
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 15)  # 25 Apr 2023 05:15 UTC + 10h = 25 Apr 2023 15:15 AEST
        self.assertEqual(dt.minute, 15)

        # Parse string format (UTC)
        dt2 = parse_rx_moment_to_sydney("2023-04-25T15:15:00Z")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.hour, 1)  # 15:15 UTC + 10h = 01:15 AEST next day
        self.assertEqual(dt2.minute, 15)

    def test_find_matching_game(self):
        # Mock DB games
        db_games = [
            {
                "id": 101,
                "game_date": datetime(2026, 5, 25, 15, 15),
                "home_team_name": "UNSW - Kentwell Cup",
                "away_team_name": "Colleagues - Kentwell Cup",
                "competition_name": "Kentwell Cup"
            },
            {
                "id": 102,
                "game_date": datetime(2026, 5, 25, 15, 15),
                "home_team_name": "Mosman",
                "away_team_name": "Two Blues",
                "competition_name": "Kentwell Cup"
            }
        ]

        # RX moment: 2026-05-25 05:15:00 UTC -> 2026-05-25 15:15:00 Sydney (AEST = +10)
        moment_val = 1779686100000  # 2026-05-25 05:15:00 UTC
        
        # Match 1: UNSW vs Colleagues (Kentwell Cup matches)
        game_id = find_matching_game(
            app_moment=parse_rx_moment_to_sydney(moment_val),
            app_home_team="University of New South Wales",
            app_away_team="Colleagues",
            db_games=db_games,
            app_competition_name="Suburban Div 1 - Kentwell Cup"
        )
        self.assertEqual(game_id, 101)

        # Match 2: Mosman vs Western Sydney Two Blues (Kentwell Cup matches)
        game_id2 = find_matching_game(
            app_moment=parse_rx_moment_to_sydney(moment_val),
            app_home_team="Mosman RUFC",
            app_away_team="Western Sydney Two Blues",
            db_games=db_games,
            app_competition_name="Kentwell Cup"
        )
        self.assertEqual(game_id2, 102)

        # Should match within 45-minute window (e.g. 20 minutes difference)
        moment_within = moment_val + 20 * 60 * 1000 # 20 minutes
        game_id3 = find_matching_game(
            app_moment=parse_rx_moment_to_sydney(moment_within),
            app_home_team="Mosman RUFC",
            app_away_team="Western Sydney Two Blues",
            db_games=db_games,
            app_competition_name="Kentwell Cup"
        )
        self.assertEqual(game_id3, 102)

        # Out of time window match (e.g. 50 minutes difference)
        moment_far = moment_val + 50 * 60 * 1000 # 50 minutes
        game_id4 = find_matching_game(
            app_moment=parse_rx_moment_to_sydney(moment_far),
            app_home_team="Mosman RUFC",
            app_away_team="Western Sydney Two Blues",
            db_games=db_games,
            app_competition_name="Kentwell Cup"
        )
        self.assertIsNone(game_id4)

        # Should still match with non-matching competition name (disabled check)
        game_id5 = find_matching_game(
            app_moment=parse_rx_moment_to_sydney(moment_val),
            app_home_team="Mosman RUFC",
            app_away_team="Western Sydney Two Blues",
            db_games=db_games,
            app_competition_name="Burke Cup"
        )
        self.assertEqual(game_id5, 102)

if __name__ == "__main__":
    unittest.main()
