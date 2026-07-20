import os
import sys
import logging
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

# Add backend root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.ingestion.engine import get_sync_engine
from src.core.config import get_settings
from src.ratings.player_impact_service import recalculate_all_impacts
import src.core.models  # noqa: F401

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ingestion")


def main():
    logger.info("Initializing Player Impact Rating backfill...")
    engine = get_sync_engine()
    SessionLocal = sessionmaker(bind=engine)
    
    settings = get_settings()
    current_year = settings.current_season_year

    recalculate_all_impacts(SessionLocal, current_year)

    # Query and log top-5 highest impact players per competition mapping
    session = SessionLocal()
    try:
        query = session.execute(
            text("""
                WITH ranked_players AS (
                    SELECT 
                        p.name as player_name,
                        c.name as club_name,
                        cm.name as comp_mapping_name,
                        pis.impact_score,
                        pis.confidence,
                        pis.games_with,
                        ROW_NUMBER() OVER (
                            PARTITION BY pis.competition_mapping_id 
                            ORDER BY pis.impact_score DESC
                        ) as rank
                    FROM player_impact_scores pis
                    JOIN players p ON pis.player_id = p.id
                    JOIN clubs c ON pis.club_id = c.id
                    JOIN competition_mapping cm ON pis.competition_mapping_id = cm.id
                    WHERE pis.year IS NULL AND pis.confidence IN ('high', 'medium')
                )
                SELECT comp_mapping_name, player_name, club_name, impact_score, confidence, games_with
                FROM ranked_players
                WHERE rank <= 5
                ORDER BY comp_mapping_name, impact_score DESC
            """)
        ).fetchall()

        logger.info("\n=== Top Impact Players per Division ===")
        current_division = None
        for row in query:
            comp_name, player_name, club_name, score, conf, games = row
            if comp_name != current_division:
                current_division = comp_name
                logger.info(f"\nDivision: {current_division}")
            logger.info(f"  • {player_name} ({club_name}) - Score: {score} [Confidence: {conf}, Games: {games}]")

    except Exception as e:
        logger.error(f"Failed to query top players: {e}")
    finally:
        session.close()

    logger.info("\nPlayer Impact Rating backfill successfully completed!")


if __name__ == "__main__":
    main()
