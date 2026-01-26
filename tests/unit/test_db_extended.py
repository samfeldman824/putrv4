"""Extended unit tests for database configuration - covering URL normalization."""

import os
from unittest.mock import patch


class TestDatabaseUrlNormalization:
    """Tests for database URL normalization in db.py."""

    def test_postgres_url_normalized_to_postgresql_psycopg(self):
        """Test that postgres:// URL is converted to postgresql+psycopg://."""
        test_url = "postgres://user:pass@host:5432/db"

        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            # Re-import to trigger URL normalization
            import importlib

            import src.core.db

            importlib.reload(src.core.db)

            # Check the normalized URL
            assert src.core.db.postgres_url.startswith("postgresql+psycopg://")
            assert "postgres://" not in src.core.db.postgres_url

    def test_postgresql_url_without_driver_normalized(self):
        """Test that postgresql:// URL without driver gets psycopg driver added."""
        test_url = "postgresql://user:pass@host:5432/db"

        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            import importlib

            import src.core.db

            importlib.reload(src.core.db)

            assert "+psycopg" in src.core.db.postgres_url

    def test_postgresql_psycopg_url_unchanged(self):
        """Test that postgresql+psycopg:// URL is not modified."""
        test_url = "postgresql+psycopg://user:pass@host:5432/db"

        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            import importlib

            import src.core.db

            importlib.reload(src.core.db)

            assert src.core.db.postgres_url == test_url

    def test_default_url_used_when_env_not_set(self):
        """Test that default localhost URL is used when DATABASE_URL not set."""
        # Remove DATABASE_URL from environment
        env_without_db = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}

        with patch.dict(os.environ, env_without_db, clear=True):
            import importlib

            import src.core.db

            importlib.reload(src.core.db)

            assert "localhost" in src.core.db.postgres_url
            assert "5433" in src.core.db.postgres_url
