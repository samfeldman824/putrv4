from fastapi import APIRouter
from sqlmodel import select

from src.api.deps import SessionDep
from src.models import Player

router = APIRouter()


@router.get("/", response_model=list[Player])
def read_players(
    session: SessionDep, offset: int = 0, limit: int = 100
) -> list[Player]:
    """Retrieve a paginated list of players from the database."""
    return list(session.exec(select(Player).offset(offset).limit(limit)).all())


@router.get("/{player_id}", response_model=Player)
def read_player(player_id: int, session: SessionDep) -> Player | None:
    """Retrieve a specific player by ID from the database."""
    return session.get(Player, player_id)
