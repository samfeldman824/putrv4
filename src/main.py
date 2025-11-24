"""FastAPI application for PUTR v4 with SQLModel database integration."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1.router import api_router
from src.core.db import create_db_and_tables


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    create_db_and_tables()
    await asyncio.sleep(0)  # Satisfy RUF029 (async function must await)
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(api_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Return welcome message for the root endpoint."""
    return {"message": "Welcome to PUTR v4 API"}
