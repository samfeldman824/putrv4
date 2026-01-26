"""Extended unit tests for game service - covering OSError handling."""

from io import BytesIO
from unittest.mock import MagicMock, mock_open, patch

from fastapi import UploadFile

from src.services.game_service import process_uploaded_file


class TestProcessUploadedFileOsError:
    """Tests for OSError handling in process_uploaded_file."""

    def test_handles_oserror_when_saving_file(self):
        """Test that OSError during file save returns error status."""
        # Create mock UploadFile
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "ledger23_11_01.csv"
        mock_file.file = BytesIO(b"player_nickname,net\nAlice,100\n")

        # Mock Path.open to raise OSError
        with patch("src.services.game_service.Path.mkdir"), patch(
            "src.services.game_service.Path.open",
            side_effect=OSError("Disk full")
        ):
            result = process_uploaded_file(mock_file)

        assert result.status == "error"
        assert result.filename == "ledger23_11_01.csv"
        assert "Disk full" in result.message

    def test_handles_permission_error(self):
        """Test that permission errors are handled gracefully."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "ledger23_11_02.csv"
        mock_file.file = BytesIO(b"content")

        with patch("src.services.game_service.Path.mkdir"), patch(
            "src.services.game_service.Path.open",
            side_effect=PermissionError("Permission denied")
        ):
            result = process_uploaded_file(mock_file)

        assert result.status == "error"
        assert "Permission denied" in result.message

    def test_no_filename_returns_unknown(self):
        """Test that file without filename returns 'unknown'."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = None

        result = process_uploaded_file(mock_file)

        assert result.filename == "unknown"
        assert result.status == "error"
        assert "No filename" in result.message

    def test_empty_filename_returns_unknown(self):
        """Test that empty filename returns error."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = ""

        result = process_uploaded_file(mock_file)

        assert result.filename == "unknown"
        assert result.status == "error"

    def test_non_csv_file_rejected(self):
        """Test that non-CSV files are rejected."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "ledger.txt"

        result = process_uploaded_file(mock_file)

        assert result.status == "error"
        assert "CSV" in result.message

    def test_handles_read_error_during_copy(self):
        """Test handling of read errors during file copy."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "ledger23_11_03.csv"
        # Create file that raises error when read
        mock_file.file = MagicMock()
        mock_file.file.read = MagicMock(side_effect=OSError("Read error"))

        # shutil.copyfileobj will call read on the source
        with patch("src.services.game_service.Path.mkdir"):
            with patch("src.services.game_service.shutil.copyfileobj") as mock_copy:
                mock_copy.side_effect = OSError("Copy failed")
                with patch(
                    "src.services.game_service.Path.open",
                    mock_open()
                ):
                    result = process_uploaded_file(mock_file)

        assert result.status == "error"


class TestProcessUploadedFileSqlAlchemyError:
    """Tests for SQLAlchemy error handling in process_uploaded_file."""

    def test_handles_database_error_during_import(self, test_engine):
        """Test that database errors during import are handled."""
        from sqlalchemy.exc import SQLAlchemyError

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "ledger23_11_04.csv"
        mock_file.file = BytesIO(b"player_nickname,net\nAlice,100\n")

        with patch("src.services.game_service.Path.mkdir"):
            with patch("src.services.game_service.Path.open", mock_open()):
                with patch("src.services.game_service.shutil.copyfileobj"):
                    with patch(
                        "src.services.game_service.Session"
                    ) as mock_session:
                        mock_session.return_value.__enter__ = MagicMock(
                            side_effect=SQLAlchemyError("DB error")
                        )
                        result = process_uploaded_file(mock_file)

        assert result.status == "error"
        assert "import" in result.message.lower() or "DB error" in result.message
