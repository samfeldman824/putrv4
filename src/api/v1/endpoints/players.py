from fastapi import APIRouter
from loguru import logger

from src.api.deps import SessionDep
from src.core.exceptions import NotFoundError
from src.dao.player_dao import get_all_players, get_player_by_id
from src.models.models import Player

router = APIRouter()


@router.get("/", response_model=list[Player])
def read_players(
    session: SessionDep, offset: int = 0, limit: int = 100
) -> list[Player]:
    """Retrieve a paginated list of players from the database."""
    logger.info(f"Fetching players list (offset={offset}, limit={limit})")
    players = get_all_players(session, offset=offset, limit=limit)
    logger.debug(f"Retrieved {len(players)} players")
    return players


@router.get("/{player_id}", response_model=Player)
def read_player(player_id: int, session: SessionDep) -> Player:
    """Retrieve a specific player by ID from the database."""
    logger.info(f"Fetching player with ID: {player_id}")
    player = get_player_by_id(session, player_id)
    if not player:
        raise NotFoundError(
            message=f"Player {player_id} not found",
            details={"resource": "player", "id": player_id},
        )
    logger.debug(f"Found player: {player.name}")
    return player
