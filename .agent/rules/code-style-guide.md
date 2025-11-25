---
trigger: always_on
---

# Agent Rules & Project Guidelines

This document outlines the rules, guidelines, and key commands for working on this repository.

## Project Overview

*   **Type**: Ultra-Strict Python Project
*   **Core Stack**: Python 3.12+, FastAPI, SQLModel, Pydantic v2
*   **Tooling**: `uv` (dependency management), `ruff` (linting/formatting), `basedpyright` (static type checking), `poethepoet` (task runner)
*   **Strictness**: Maximum. TypeScript strict mode equivalent. No `Any`, no untyped functions, strict null safety.
*   **Logging**: Loguru

## Key Commands

All commands should be run using `uv run` or directly if the environment is activated. The project uses `poethepoet` for task management.

### Development
*   **Start Dev Server**: `uv run poe dev`
    *   Runs `uvicorn src.main:app --reload --port 8000`

### Code Quality & Testing
*   **Format & Fix**: `uv run poe format`
    *   Runs `ruff format`, `ruff check --fix`, and `basedpyright`.
    *   **Run this before submitting changes.**
*   **Check (No Fix)**: `uv run poe check`
    *   Runs linting and type checking without modifying files.
*   **Lint Only**: `uv run poe lint`
*   **Full Quality Gate**: `uv run poe quality`
    *   Runs formatting, linting, type checking, and complexity metrics.

### Data Management
*   **Import CSV**: `uv run poe import-csv`
    *   Imports ledger files into PostgreSQL.

## Development Guidelines

1.  **Strict Typing**:
    *   Every function argument and return value must be typed.
    *   Avoid `Any`. Use specific types or Generics.
    *   `basedpyright` is configured to be extremely strict (similar to TS `strict: true`).

2.  **Code Style**:
    *   Follow `ruff` configuration.
    *   Docstrings are encouraged (Google style).
    *   Keep complexity low (McCabe complexity < 10).

3.  **Dependency Management**:
    *   Use `uv add <package>` to add dependencies.
    *   Use `uv add --dev <package>` for dev dependencies.
    *   Never use `pip` directly.

4.  **File Structure**:
    *   `src/`: Source code
        *   `api/`: API endpoints and routers
        *   `core/`: Core configuration and utilities
        *   `models.py`: Database models (SQLModel)
        *   `schemas/`: Pydantic schemas (Request/Response)
        *   `services/`: Business logic
        *   `main.py`: Application entry point
    *   `tests/`: Tests

## Environment

*   Ensure a `.env` file is present (referenced by `python-dotenv`).
*   PostgreSQL is used as the database.