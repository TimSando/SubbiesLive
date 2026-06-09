"""Background scheduler configuration for the data ingestion pipeline.

Runs as part of the FastAPI application lifespan, setting up the daily
and game day sync cycles via APScheduler.
"""

import os
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import sessionmaker

from src.ingestion.engine import get_sync_engine
from src.ingestion.service import run_ingestion
from src.scripts.seed_mapping import seed_mapping

logger = logging.getLogger("ingestion")
TIMEZONE = os.environ.get("TZ", "Australia/Sydney")

# Global reference to control lifecycle
_scheduler: BackgroundScheduler | None = None


def start_ingestion_scheduler():
    """Start the ingestion scheduler as a background thread.

    Called from FastAPI's lifespan startup hook.
    """
    global _scheduler

    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)

    # Run initial ingestion in a background thread so it doesn't block startup
    def _initial_run():
        logger.info("Checking for competition mapping seed...")
        try:
            csv_path = os.environ.get(
                "MAPPING_CSV_PATH",
                "/app/src/scripts/competition_parent_mapping - Sheet1.csv",
            )
            seed_mapping(csv_path)
        except Exception as e:
            logger.error(f"Failed to seed mapping: {e}")

        logger.info("Running initial data ingestion...")
        run_ingestion(Session)

        logger.info("Checking for missing club details to seed...")
        try:
            from src.scripts.seed_club_details import seed_club_details_if_empty

            seed_club_details_if_empty()
        except Exception as e:
            logger.error(f"Failed to automatically seed club details: {e}")

        logger.info("Checking for missing club competition mappings...")
        try:
            from src.scripts.seed_mapping import seed_clubs_from_json

            json_path = os.environ.get(
                "PARENT_CLUB_JSON_PATH", "/app/src/scripts/parent_club.json"
            )
            seed_clubs_from_json(json_path)
        except Exception as e:
            logger.error(f"Failed to automatically seed club competition mappings: {e}")

    init_thread = threading.Thread(target=_initial_run, daemon=True)
    init_thread.start()

    # Set up scheduled jobs
    _scheduler = BackgroundScheduler(timezone=TIMEZONE)

    # Sunday evening at 6:00 PM
    _scheduler.add_job(
        run_ingestion,
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=TIMEZONE),
        args=[Session],
        id="sunday_evening_ingestion",
        name="Sunday evening ingestion (Sun 6:00 PM)",
    )

    # Saturday morning at 1:00 AM
    _scheduler.add_job(
        run_ingestion,
        CronTrigger(day_of_week="sat", hour=1, minute=0, timezone=TIMEZONE),
        args=[Session],
        id="saturday_morning_ingestion",
        name="Saturday morning ingestion (Sat 1:00 AM)",
    )

    # Game day sync every 15 min on Saturday, 9 AM - 6 PM
    _scheduler.add_job(
        run_ingestion,
        CronTrigger(
            day_of_week="sat", hour="9-20", minute="0,15,30,45", timezone=TIMEZONE
        ),
        args=[Session],
        id="gameday_ingestion",
        name="Game day ingestion (Sat every 15 min, 9 AM - 6 PM)",
    )

    # NSWRugbyTV video URL ingestion (Sat hourly 9 AM - 7 PM)
    try:
        from src.scripts.ingest_nswrugbytv import ingest_nswrugbytv_videos

        _scheduler.add_job(
            ingest_nswrugbytv_videos,
            CronTrigger(day_of_week="sat", hour="9-19", minute=0, timezone=TIMEZONE),
            args=[engine],
            id="video_ingestion",
            name="NSWRugbyTV video ingestion (Sat hourly 9 AM - 7 PM)",
        )
    except Exception as e:
        logger.error(f"Failed to schedule video ingestion job: {e}")

    _scheduler.start()

    logger.info("Ingestion scheduler started:")
    logger.info("  • Sunday: 6:00 PM AEST")
    logger.info("  • Saturday: 1:00 AM AEST")
    logger.info("  • Saturday: Every 15 min, 9:00 AM - 6:00 PM AEST")
    logger.info(
        "  • Saturday: NSWRugbyTV video ingestion hourly, 9:00 AM - 7:00 PM AEST"
    )


def stop_ingestion_scheduler():
    """Shut down the ingestion scheduler cleanly.

    Called from FastAPI's lifespan shutdown hook.
    """
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Ingestion scheduler stopped.")
        _scheduler = None
