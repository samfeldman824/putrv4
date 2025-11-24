from sqlmodel import SQLModel, create_engine

# Database setup
# Using standard psycopg driver for simplicity first
# For async support later, we would use: postgresql+asyncpg://...
# Port 5433 to avoid conflicts
POSTGRES_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/putr"

engine = create_engine(POSTGRES_URL)


def create_db_and_tables() -> None:
    """Create database tables from SQLModel metadata."""
    SQLModel.metadata.create_all(engine)
