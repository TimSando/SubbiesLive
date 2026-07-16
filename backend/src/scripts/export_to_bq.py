import csv
import io
import logging
import os
from google.cloud import bigquery
from sqlalchemy import text
from src.ingestion.engine import get_sync_engine

logger = logging.getLogger("bq_export")

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


def export_db_to_bq():
    """Export main database tables to CSV format in memory and load them into BigQuery."""
    dataset_id = os.environ.get("GCP_BQ_DATASET")
    if not dataset_id:
        logger.error("GCP_BQ_DATASET environment variable is not set. Skipping export.")
        return

    logger.info("Starting database export to BigQuery dataset: %s", dataset_id)

    try:
        bq_client = bigquery.Client()
    except Exception as e:
        logger.error("Failed to initialize BigQuery client: %s", e)
        return

    try:
        engine = get_sync_engine()
    except Exception as e:
        logger.error("Failed to get database engine: %s", e)
        return

    for table in TABLES_TO_EXPORT:
        logger.info("Exporting table to BigQuery: %s", table)
        try:
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)

            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table}"))
                # Write header
                writer.writerow(result.keys())
                # Write rows
                writer.writerows(result.fetchall())

            csv_data = csv_buffer.getvalue()
            csv_buffer.close()

            # Convert string data to bytes stream
            file_like = io.BytesIO(csv_data.encode("utf-8"))

            # Construct table reference
            table_ref = bq_client.dataset(dataset_id).table(table)

            # Configure load job
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.CSV,
                skip_leading_rows=1,
                autodetect=True,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            )

            # Start the load job
            job = bq_client.load_table_from_file(
                file_like, table_ref, job_config=job_config
            )
            job.result()  # Wait for the load job to complete

            logger.info("Successfully loaded table %s into BigQuery", table)

        except Exception as e:
            logger.error("Failed to export and upload table %s: %s", table, e)

    logger.info("Database export to BigQuery completed.")


if __name__ == "__main__":
    import sys

    # Ensure project root is in the path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    logging.basicConfig(level=logging.INFO)
    export_db_to_bq()
