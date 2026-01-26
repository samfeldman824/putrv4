"""Custom exception classes for consistent error handling across the application."""

from dataclasses import dataclass, field

# Shared type alias for error detail values
type ErrorDetails = dict[
    str, str | int | float | bool | list[str] | list[dict[str, str | int]] | None
]


@dataclass
class AppError(Exception):
    """Base exception for all application errors."""

    code: str = "app_error"
    message: str = "An application error occurred"
    details: ErrorDetails = field(default_factory=dict)

    def __str__(self) -> str:  # pyright: ignore[reportImplicitOverride]
        return self.message


@dataclass
class NotFoundError(AppError):
    """Raised when a requested resource is not found."""

    code: str = "not_found"
    message: str = "Resource not found"


@dataclass
class ValidationError(AppError):
    """Raised when domain validation fails."""

    code: str = "validation_error"
    message: str = "Validation failed"


@dataclass
class ConflictError(AppError):
    """Raised when an operation conflicts with existing state."""

    code: str = "conflict"
    message: str = "Resource conflict"


@dataclass
class InternalError(AppError):
    """Raised for unexpected internal errors."""

    code: str = "internal_error"
    message: str = "Internal server error"
