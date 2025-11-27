import os

from dotenv import load_dotenv
from loguru import logger
from sqlmodel import SQLModel, create_engine

# Load environment variables from .env file
load_dotenv()

# Database setup
# Using standard psycopg driver for simplicity first
# For async support later, we would use: postgresql+asyncpg://...
# Get DATABASE_URL from environment, fallback to local development
postgres_url = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/putr",
)

# Render provides postgres:// URLs, but SQLAlchemy needs postgresql://
# Also ensure we're using the psycopg driver (not psycopg2)
if postgres_url.startswith("postgres://"):
    postgres_url = postgres_url.replace("postgres://", "postgresql+psycopg://", 1)
elif postgres_url.startswith("postgresql://") and "+psycopg" not in postgres_url:
    postgres_url = postgres_url.replace("postgresql://", "postgresql+psycopg://", 1)

logger.info(f"Initializing database engine with URL: {postgres_url.split('@')[1]}")
engine = create_engine(postgres_url)


def create_db_and_tables() -> None:
    """Create database tables from SQLModel metadata."""
    logger.info("Creating database tables from SQLModel metadata...")
    SQLModel.metadata.create_all(engine)
    logger.success("Database tables created successfully")
