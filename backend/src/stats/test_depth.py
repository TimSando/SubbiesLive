import unittest
import asyncio
from src.core.database import async_session_factory
from src.stats.repository import get_club_depth_stats


class TestStatsDepthQuery(unittest.IsolatedAsyncioTestCase):
    async def test_get_club_depth_stats(self):
        async with async_session_factory() as session:
            # Query stats from the database (should have some seed data)
            stats = await get_club_depth_stats(session)
            self.assertIsInstance(stats, list)

            if len(stats) > 0:
                first = stats[0]
                self.assertIsNotNone(first.club_name)
                self.assertIsNotNone(first.club_id)
                self.assertGreaterEqual(first.total_players, 0)
                self.assertGreaterEqual(first.core_players, 0)
                self.assertGreaterEqual(first.dedicated_players, 0)
                self.assertGreaterEqual(first.swing_players, 0)
                self.assertGreaterEqual(first.avg_games, 0.0)

                print(f"\n[Test stats output] Club: {first.club_name}")
                print(f"Total active players: {first.total_players}")
                print(f"Core players (>=5 games): {first.core_players}")
                print(f"Dedicated players: {first.dedicated_players}")
                print(f"Swing players: {first.swing_players}")
                print(f"Average games per player: {first.avg_games:.2f}")


if __name__ == "__main__":
    unittest.main()
