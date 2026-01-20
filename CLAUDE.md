# CLAUDE.md

## Project Overview

PUTR v4 - Ultra-strict Python 3.12+ FastAPI application for tracking poker game ledgers with PostgreSQL.

**Tech Stack**: Python 3.12+, FastAPI, SQLModel, Pydantic v2, PostgreSQL, psycopg, loguru

**Tooling**: `uv` (package manager), `ruff` (linting/formatting), `basedpyright` (strict type checking), `poethepoet` (task runner)

## Quick Commands

```bash
# Development
uv run poe dev              # Start dev server (localhost:8000)
uv run pytest               # Run tests (80% coverage required)

# Code Quality (run before committing)
uv run poe format           # Format + fix + type check
uv run poe check            # Lint + type check (no fixes)
uv run poe quality          # Full quality gate

# Data
uv run poe import-csv       # Import ledger CSV files

# Dependencies
uv add <package>            # Add production dependency
uv add --dev <package>      # Add dev dependency
uv sync                     # Install all dependencies
```

## Project Structure

```
src/
├── api/v1/endpoints/       # FastAPI endpoints (players.py, games.py)
├── core/                   # Database config, logging
├── models/                 # SQLModel database models
├── schemas/                # Pydantic request/response schemas
├── services/               # Business logic layer
├── dao/                    # Data access objects
└── main.py                 # App entry point
tests/
├── unit/                   # Unit tests
├── integration/            # API integration tests
└── conftest.py             # Shared fixtures
```

## Coding Standards

### Type Safety (STRICT - No Exceptions)
- Every function must have full type annotations (arguments + return)
- No `Any` types - use specific types or Generics
- Handle `Optional`/`None` explicitly (strict null safety)
- `basedpyright` runs in strict mode (TypeScript equivalent)

### Code Quality
- McCabe complexity: max 10
- Nested blocks: max 3
- No print statements (use loguru)
- No commented-out code
- Google-style docstrings

### Testing
- 80% coverage required (tests fail below this)
- Tests use in-memory SQLite (fast, isolated)
- Unit tests in `tests/unit/`, integration in `tests/integration/`
- Warnings treated as errors

## API Endpoints

- `GET /api/v1/players` - List players (paginated)
- `GET /api/v1/players/{id}` - Get player
- `POST /api/v1/games/upload` - Upload CSV ledger(s)
- `GET /` - Health check
- `GET /docs` - Swagger UI

## Database Models

Key models in `src/models/models.py`:
- **Player**: Core entity (id, name, putr, net, stats)
- **Game**: Poker session (id, date_str in `YY_MM_DD` or `YY_MM_DD(N)` format, where `N` distinguishes multiple games on the same day)
- **PlayerNickname**: Alias mapping for CSV import
- **PlayerGameStats**: Player-Game results (net per game)
- **LedgerEntry**: Raw CSV row data

## Environment Setup

```bash
# Copy env template
cp .env.example .env

# Start PostgreSQL
docker-compose up -d        # postgres:16-alpine on port 5433

# Required env vars
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/putr
```

## CI/CD

GitHub Actions runs on all commits:
1. Lint + Type Check (`uv run poe check`)
2. Tests with coverage (Python 3.12 & 3.13)
3. Security scanning (Bandit, CodeQL, OSV Scanner)
4. SonarCloud analysis

Production deploys to Render.com via `render.yaml` blueprint.
