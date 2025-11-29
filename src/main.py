"""FastAPI application for PUTR v4 with SQLModel database integration."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.v1.router import api_router
from src.core.db import create_db_and_tables
from src.core.logging_config import configure_logging
from src.services.import_service import add_records


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    configure_logging()
    logger.info("Starting PUTR v4 application...")
    logger.info("Initializing database...")
    create_db_and_tables()
    logger.success("Database initialized successfully")
    logger.info("Importing player data...")
    add_records()
    logger.success("Player data imported successfully")
    await asyncio.sleep(0)  # Satisfy RUF029 (async function must await)
    logger.success("Application startup complete")
    yield
    logger.info("Shutting down PUTR v4 application...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Return welcome message for the root endpoint."""
    logger.debug("Root endpoint accessed")
    return {"message": "Welcome to PUTR v4 API"}
