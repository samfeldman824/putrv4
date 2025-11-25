"""Script to import CSV ledger files into PostgreSQL database."""

from loguru import logger

from src.core.logging_config import configure_logging
from src.services.import_service import (
    add_records,
    reset_db,
)

if __name__ == "__main__":
    configure_logging()
    logger.info("Starting CSV import script...")
    logger.info("Resetting database...")
    reset_db()
    logger.info("Adding player records from backup...")
    add_records()
    logger.success("CSV import script completed successfully")
