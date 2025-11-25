from loguru import logger
from sqlmodel import SQLModel, create_engine

# Database setup
# Using standard psycopg driver for simplicity first
# For async support later, we would use: postgresql+asyncpg://...
# Port 5433 to avoid conflicts
POSTGRES_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/putr"

logger.info(f"Initializing database engine with URL: {POSTGRES_URL.split('@')[1]}")
engine = create_engine(POSTGRES_URL)


def create_db_and_tables() -> None:
    """Create database tables from SQLModel metadata."""
    logger.info("Creating database tables from SQLModel metadata...")
    SQLModel.metadata.create_all(engine)
    logger.success("Database tables created successfully")
