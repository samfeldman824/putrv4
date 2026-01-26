"""Unit tests for game service."""

from io import BytesIO
from unittest.mock import MagicMock, patch

from fastapi import UploadFile
import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.services.game_service import process_uploaded_file
from src.services.import_service import ImportResult


class TestProcessUploadedFile:
    """Tests for process_uploaded_file."""

    def test_missing_filename_returns_error(self):
        """Test that missing filename returns error status."""
        file = MagicMock(spec=UploadFile)
        file.filename = None

        result = process_uploaded_file(file)

        assert result.status == "error"
        assert result.filename == "unknown"
        assert "filename" in result.message.lower()

    def test_non_csv_file_returns_error(self):
        """Test that non-CSV file returns error status."""
        file = MagicMock(spec=UploadFile)
        file.filename = "test.txt"

        result = process_uploaded_file(file)

        assert result.status == "error"
        assert result.filename == "test.txt"
        assert "CSV" in result.message

    def test_path_traversal_sanitized(self, mock_ledgers_dir):
        """Test that path traversal attempts are sanitized (S2083)."""
        file_content = b"player_nickname,player_id,buy_in,buy_out,stack,net\n"
        file = MagicMock(spec=UploadFile)
        # Attempt path traversal - should be sanitized to just "passwd.csv"
        file.filename = "../../../etc/passwd.csv"
        file.file = BytesIO(file_content)

        with (
            patch("src.services.game_service.import_single_ledger") as mock_import,
            patch("src.services.game_service.Session"),
        ):
            mock_import.return_value = ImportResult.SUCCESS
            result = process_uploaded_file(file)

        # The filename should be sanitized to just the base name
        assert result.filename == "passwd.csv"
        # Verify file was written to the safe location, not outside
        saved_file = mock_ledgers_dir / "passwd.csv"
        assert saved_file.exists()

    def test_path_traversal_with_backslash_sanitized(self, mock_ledgers_dir):
        """Test that Windows-style path traversal is sanitized.

        On Unix, backslashes are valid filename characters, so Path.name returns
        the whole string as the filename. This is safe because the file stays
        in the ledgers directory regardless.
        """
        file_content = b"player_nickname,player_id,buy_in,buy_out,stack,net\n"
        file = MagicMock(spec=UploadFile)
        file.filename = "..\\..\\..\\etc\\passwd.csv"
        file.file = BytesIO(file_content)

        with (
            patch("src.services.game_service.import_single_ledger") as mock_import,
            patch("src.services.game_service.Session"),
        ):
            mock_import.return_value = ImportResult.SUCCESS
            result = process_uploaded_file(file)

        # On Unix, backslashes are part of the filename (not path separators)
        # The file is safely written to the ledgers directory with backslashes in the name
        assert result.status == "success"
        # On Unix, the actual saved filename includes the backslashes
        saved_file = mock_ledgers_dir / "..\\..\\..\\etc\\passwd.csv"
        assert saved_file.exists()

    @pytest.fixture
    def mock_ledgers_dir(self, tmp_path, monkeypatch):
        """Set up temporary ledgers directory."""
        ledgers_dir = tmp_path / "ledgers"
        ledgers_dir.mkdir()
        monkeypatch.chdir(tmp_path)
        return ledgers_dir

    def test_successful_import_returns_success(self, mock_ledgers_dir):
        """Test that successful import returns success and writes file."""
        file_content = b"player_nickname,player_id,buy_in,buy_out,stack,net\n"
        file = MagicMock(spec=UploadFile)
        file.filename = "ledger23_12_10.csv"
        file.file = BytesIO(file_content)

        with (
            patch("src.services.game_service.import_single_ledger") as mock_import,
            patch("src.services.game_service.Session"),
        ):
            mock_import.return_value = ImportResult.SUCCESS

            result = process_uploaded_file(file)

        assert result.status == "success"
        assert result.filename == "ledger23_12_10.csv"
        # Verify file was written
        saved_file = mock_ledgers_dir / "ledger23_12_10.csv"
        assert saved_file.exists()
        assert saved_file.read_bytes() == file_content

    def test_game_exists_returns_skipped(self, mock_ledgers_dir):
        """Test that game already exists returns skipped and writes file."""
        file_content = b"player_nickname,player_id,buy_in,buy_out,stack,net\n"
        file = MagicMock(spec=UploadFile)
        file.filename = "ledger23_12_11.csv"
        file.file = BytesIO(file_content)

        with (
            patch("src.services.game_service.import_single_ledger") as mock_import,
            patch("src.services.game_service.Session"),
        ):
            mock_import.return_value = ImportResult.GAME_EXISTS

            result = process_uploaded_file(file)

        assert result.status == "skipped"
        assert "already exists" in result.message.lower()
        # Verify file was still written
        saved_file = mock_ledgers_dir / "ledger23_12_11.csv"
        assert saved_file.exists()

    def test_missing_nicknames_returns_error(self, mock_ledgers_dir):
        """Test that missing nicknames returns error and writes file."""
        file_content = b"player_nickname,player_id,buy_in,buy_out,stack,net\n"
        file = MagicMock(spec=UploadFile)
        file.filename = "ledger23_12_12.csv"
        file.file = BytesIO(file_content)

        with (
            patch("src.services.game_service.import_single_ledger") as mock_import,
            patch("src.services.game_service.Session"),
        ):
            mock_import.return_value = ImportResult.MISSING_NICKNAMES

            result = process_uploaded_file(file)

        assert result.status == "error"
        assert "nickname" in result.message.lower()
        # Verify file was still written
        saved_file = mock_ledgers_dir / "ledger23_12_12.csv"
        assert saved_file.exists()

    def test_sqlalchemy_error_returns_error(self, mock_ledgers_dir):
        """Test that SQLAlchemyError during import returns error."""
        file_content = b"player_nickname,player_id,buy_in,buy_out,stack,net\n"
        file = MagicMock(spec=UploadFile)
        file.filename = "ledger23_12_13.csv"
        file.file = BytesIO(file_content)

        with patch("src.services.game_service.Session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(
                side_effect=SQLAlchemyError("DB error")
            )

            result = process_uploaded_file(file)

        assert result.status == "error"
        assert "import" in result.message.lower() or "error" in result.message.lower()
        # Verify file was still written before the error
        saved_file = mock_ledgers_dir / "ledger23_12_13.csv"
        assert saved_file.exists()
