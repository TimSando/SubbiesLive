import csv
import io
import logging
import os
from datetime import datetime
from google.cloud import storage
from sqlalchemy import text
from src.ingestion.engine import get_sync_engine

logger = logging.getLogger("gcp_export")

TABLES_TO_EXPORT = [
    "clubs",
    "competition_mapping",
    "competitions",
    "game_events",
    "games",
    "player_history",
    "players",
    "rounds",
    "teams",
    "venues",
]


def export_db_to_gcp():
    """Export main database tables to CSV and upload them to a GCP bucket."""
    bucket_name = os.environ.get("GCP_BUCKET_NAME")
    if not bucket_name:
        logger.error(
            "GCP_BUCKET_NAME environment variable is not set. Skipping export."
        )
        return

    logger.info("Starting database export to GCP bucket: %s", bucket_name)

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
    except Exception as e:
        logger.error("Failed to initialize GCP storage client: %s", e)
        return

    try:
        engine = get_sync_engine()
    except Exception as e:
        logger.error("Failed to get database engine: %s", e)
        return

    date_str = datetime.now().strftime("%Y-%m-%d")

    for table in TABLES_TO_EXPORT:
        logger.info("Exporting table: %s", table)
        try:
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)

            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table}"))
                # Write header
                writer.writerow(result.keys())
                # Write rows
                writer.writerows(
                    conn.execute(text(f"SELECT * FROM {table}")).fetchall()
                )

            csv_data = csv_buffer.getvalue()
            csv_buffer.close()

            # Upload to date-specific folder
            date_blob_path = f"exports/{date_str}/{table}.csv"
            date_blob = bucket.blob(date_blob_path)
            date_blob.upload_from_string(csv_data, content_type="text/csv")
            logger.info("Uploaded to %s", date_blob_path)

            # Upload to latest folder
            latest_blob_path = f"latest/{table}.csv"
            latest_blob = bucket.blob(latest_blob_path)
            latest_blob.upload_from_string(csv_data, content_type="text/csv")
            logger.info("Uploaded to %s", latest_blob_path)

        except Exception as e:
            logger.error("Failed to export and upload table %s: %s", table, e)

    logger.info("Database export to GCP bucket completed.")


if __name__ == "__main__":
    import sys

    # Ensure project root is in the path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    logging.basicConfig(level=logging.INFO)
    export_db_to_gcp()
