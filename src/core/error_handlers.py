"""Global exception handlers for FastAPI application."""

from typing import TYPE_CHECKING, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from src.core.exceptions import (
    AppError,
    ConflictError,
    ErrorDetails,
    InternalError,
    NotFoundError,
    ValidationError,
)

if TYPE_CHECKING:
    type ErrorPayload = dict[str, dict[str, str | ErrorDetails]]


def _error_payload(
    code: str,
    message: str,
    details: ErrorDetails | None = None,
) -> "ErrorPayload":
    """Build consistent error response payload."""
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app.

    Note: The nested handler functions are registered via decorators and used by FastAPI
    at runtime, but static analysis tools cannot detect this usage pattern.
    """

    @app.exception_handler(NotFoundError)
    def not_found_handler(  # pyright: ignore[reportUnusedFunction]
        _: Request, exc: NotFoundError
    ) -> JSONResponse:
        logger.debug(f"NotFoundError: {exc.message}")
        return JSONResponse(
            status_code=404,
            content=_error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(ValidationError)
    def validation_handler(  # pyright: ignore[reportUnusedFunction]
        _: Request, exc: ValidationError
    ) -> JSONResponse:
        logger.warning(f"ValidationError: {exc.message}")
        return JSONResponse(
            status_code=422,
            content=_error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(ConflictError)
    def conflict_handler(  # pyright: ignore[reportUnusedFunction]
        _: Request, exc: ConflictError
    ) -> JSONResponse:
        logger.warning(f"ConflictError: {exc.message}")
        return JSONResponse(
            status_code=409,
            content=_error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(InternalError)
    def internal_error_handler(  # pyright: ignore[reportUnusedFunction]
        _: Request, exc: InternalError
    ) -> JSONResponse:
        logger.error(f"InternalError: {exc.message}")
        return JSONResponse(
            status_code=500,
            content=_error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(AppError)
    def app_error_handler(  # pyright: ignore[reportUnusedFunction]
        _: Request, exc: AppError
    ) -> JSONResponse:
        logger.warning(f"AppError: {exc.message}")
        return JSONResponse(
            status_code=400,
            content=_error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    def request_validation_handler(  # pyright: ignore[reportUnusedFunction]
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.debug(f"Request validation failed: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                "request_validation_error",
                "Request validation failed",
                cast("ErrorDetails", {"errors": exc.errors()}),
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    def sqlalchemy_handler(  # pyright: ignore[reportUnusedFunction]
        _: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception(f"Database error: {exc}")
        return JSONResponse(
            status_code=500,
            content=_error_payload("database_error", "Database error"),
        )

    @app.exception_handler(Exception)
    def unhandled_handler(  # pyright: ignore[reportUnusedFunction]
        _: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content=_error_payload("internal_error", "Internal server error"),
        )
