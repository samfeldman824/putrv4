"""FastAPI application for PUTR v4 with SQLModel database integration."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlmodel import Session, SQLModel, create_engine, select

from src.models import Player

# Database setup
# Using standard psycopg driver for simplicity first
# For async support later, we would use: postgresql+asyncpg://...
# Port 5433 to avoid conflicts
POSTGRES_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/putr"

engine = create_engine(POSTGRES_URL)


def create_db_and_tables() -> None:
    """Create database tables from SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Provide a database session for dependency injection."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    create_db_and_tables()
    await asyncio.sleep(0)  # Satisfy RUF029 (async function must await)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root() -> dict[str, str]:
    """Return welcome message for the root endpoint."""
    return {"message": "Welcome to PUTR v4 API"}


@app.get("/players/", response_model=list[Player])
def read_players(
    session: SessionDep, offset: int = 0, limit: int = 100
) -> list[Player]:
    """Retrieve a paginated list of players from the database."""
    return list(session.exec(select(Player).offset(offset).limit(limit)).all())


@app.get("/players/{player_id}", response_model=Player)
def read_player(player_id: int, session: SessionDep) -> Player | None:
    """Retrieve a specific player by ID from the database."""
    return session.get(Player, player_id)
