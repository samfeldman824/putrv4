# PUTR v4

Ultra-strict Python FastAPI application with PostgreSQL database.

## Tech Stack

- **Python**: 3.12+
- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLModel
- **Type Checking**: basedpyright (strict mode)
- **Linting/Formatting**: ruff
- **Dependency Management**: uv
- **Task Runner**: poethepoet

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed
- PostgreSQL running (via Docker or local)

### Installation

```bash
# Clone the repository
git clone https://github.com/samfeldman824/putrv4.git
cd putrv4

# Install dependencies
uv sync

# Copy environment variables
cp .env.example .env

# Start PostgreSQL (using Docker)
docker-compose up -d

# Run the development server
uv run poe dev
```

Visit http://localhost:8000 to see the API.
API documentation: http://localhost:8000/docs

## Development Commands

```bash
# Format code, fix issues, and type check
uv run poe format

# Run linting and type checking (no fixes)
uv run poe check

# Run quality checks (format + lint + metrics)
uv run poe quality

# Start development server
uv run poe dev

# Import CSV ledger data
uv run poe import-csv
```

## Project Structure

```
putrv4/
├── src/
│   ├── api/              # API endpoints and routers
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── router.py
│   ├── core/             # Core configuration
│   │   ├── db.py         # Database setup
│   │   └── logging_config.py
│   ├── models.py         # SQLModel database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── main.py           # FastAPI application
├── tests/                # Test files
├── ledgers/              # CSV ledger files
├── pyproject.toml        # Project configuration
└── docker-compose.yml    # PostgreSQL container
```

## Deployment

See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for detailed deployment instructions to Render (free hosting).

### Quick Deploy to Render

1. Push to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. New → Blueprint
4. Select this repository
5. Deploy!

Your app will be live at `https://putrv4-api.onrender.com`

## Code Quality Standards

This project uses **maximum strictness** settings:

- ✅ All functions must have type annotations
- ✅ No `Any` types allowed
- ✅ Strict null safety
- ✅ Maximum McCabe complexity: 10
- ✅ Maximum nested blocks: 3
- ✅ 80%+ test coverage required

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | See `.env.example` | PostgreSQL connection string |
| `ENVIRONMENT` | No | development | Application environment |
| `LOG_LEVEL` | No | INFO | Logging level |

## License

MIT
