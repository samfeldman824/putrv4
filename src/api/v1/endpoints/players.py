from fastapi import APIRouter
from loguru import logger
from sqlmodel import select

from src.api.deps import SessionDep
from src.models.models import Player

router = APIRouter()


@router.get("/", response_model=list[Player])
def read_players(
    session: SessionDep, offset: int = 0, limit: int = 100
) -> list[Player]:
    """Retrieve a paginated list of players from the database."""
    logger.info(f"Fetching players list (offset={offset}, limit={limit})")
    players = list(session.exec(select(Player).offset(offset).limit(limit)).all())
    logger.debug(f"Retrieved {len(players)} players")
    return players


@router.get("/{player_id}", response_model=Player)
def read_player(player_id: int, session: SessionDep) -> Player | None:
    """Retrieve a specific player by ID from the database."""
    logger.info(f"Fetching player with ID: {player_id}")
    player = session.get(Player, player_id)
    if player:
        logger.debug(f"Found player: {player.name}")
    else:
        logger.warning(f"Player with ID {player_id} not found")
    return player
