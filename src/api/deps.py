from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from loguru import logger
from sqlmodel import Session

from src.core.db import engine


def get_session() -> Generator[Session, None, None]:
    """Provide a database session for dependency injection."""
    logger.debug("Creating database session")
    with Session(engine) as session:
        yield session
    logger.debug("Database session closed")


SessionDep = Annotated[Session, Depends(get_session)]
