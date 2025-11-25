from fastapi import APIRouter
from loguru import logger

from src.api.v1.endpoints import games, players

logger.info("Initializing API v1 router")
api_router = APIRouter(prefix="/api/v1")

logger.debug("Registering players endpoint")
api_router.include_router(players.router, prefix="/players", tags=["players"])
logger.debug("Registering games endpoint")
api_router.include_router(games.router, prefix="/games", tags=["games"])
logger.success("API v1 router initialized successfully")
