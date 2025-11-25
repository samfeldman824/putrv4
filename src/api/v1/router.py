from fastapi import APIRouter

from src.api.v1.endpoints import players, games

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(players.router, prefix="/players", tags=["players"])
api_router.include_router(games.router, prefix="/games", tags=["games"])
