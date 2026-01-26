"""Tests to cover remaining gaps in test coverage."""

import asyncio
import contextlib
import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.api.deps import get_session
from src.api.v1.endpoints.games import upload_game_ledgers
from src.dao.player_dao import create_nickname
import src.import_csv
from src.models.models import (
    Game,
    LedgerEntry,
    Player,
    PlayerGameStats,
    PlayerNickname,
)
from src.services.import_service import (
    ImportResult,
    add_records,
    import_single_ledger,
)
from src.services.player_stats_service import recalculate_all_player_stats


class TestDepsGetSession:
    """Test the get_session dependency function from deps.py."""

    def test_get_session_yields_and_closes(self):
        """Test that get_session creates and properly closes a session."""
        # Create a test engine
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(test_engine)

        with patch("src.api.deps.engine", test_engine):
            # Call the generator
            gen = get_session()

            # Get the session
            session = next(gen)
            assert session is not None
            assert isinstance(session, Session)

            # Close the generator (triggers the cleanup after yield)
            with contextlib.suppress(StopIteration):
                next(gen)

        test_engine.dispose()


class TestGamesUploadEmptyFiles:
    """Test the empty files check in games.py upload endpoint."""

    def test_upload_with_empty_files_list_raises_400(self):
        """Test that upload_game_ledgers raises 400 for empty file list."""

        async def run_upload():
            return await upload_game_ledgers(files=[])

        # Call the endpoint function directly with empty list
        # This bypasses FastAPI's validation layer
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(run_upload())

        assert exc_info.value.status_code == 400
        assert "No files provided" in exc_info.value.detail


class TestImportServiceValueErrors:
    """Test ValueError branches in import_service.py."""

    def test_add_records_raises_when_player_id_is_none(self, test_engine):
        """Test add_records raises ValueError when player ID is None."""
        backup_data = {
            "TestPlayer": {
                "flag": "🏳️",
                "putr": "5.0",
                "player_nicknames": ["TestNick"],
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(backup_data, f)
            backup_path = f.name

        try:
            # Mock create_player to return a player with None id
            mock_player = Player(name="TestPlayer", flag="🏳️", putr="5.0")
            mock_player.id = None  # Force id to be None

            with (
                patch("src.services.import_service.engine", test_engine),
                patch(
                    "src.services.import_service.create_player",
                    return_value=mock_player,
                ),
                pytest.raises(
                    ValueError, match="Player ID should be populated after flush"
                ),
            ):
                add_records(backup_path)
        finally:
            Path(backup_path).unlink()

    def test_import_single_ledger_raises_when_game_id_is_none(
        self, session, sample_player
    ):
        """Test import_single_ledger raises ValueError when game ID is None."""
        # Create nickname for the player
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )
        session.commit()

        # Create a valid ledger file
        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,200,200,100\n"
        )
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / "ledger23_99_01.csv"
        temp_path.write_text(csv_content)

        try:
            # Mock create_game to return a game with None id
            mock_game = Game(date_str="23_99_01", ledger_filename="ledger23_99_01.csv")
            mock_game.id = None

            with (
                patch(
                    "src.services.import_service.create_game", return_value=mock_game
                ),
                pytest.raises(
                    ValueError, match="Game ID should be populated after flush"
                ),
            ):
                import_single_ledger(session, temp_path)
        finally:
            temp_path.unlink()

    def test_import_single_ledger_raises_when_player_id_is_none_in_loop(self, session):
        """Test import_single_ledger raises ValueError when player ID is None."""
        # Create a player that will have None id in the validation result
        player = Player(name="TestPlayer", flag="🏳️", putr="5.0")
        session.add(player)
        session.flush()

        # Create nickname
        create_nickname(
            session,
            PlayerNickname(
                nickname="TestPlayer",
                player_name="TestPlayer",
                player_id=player.id,
            ),
        )
        session.commit()

        # Create ledger file
        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            "TestPlayer,id1,100,200,200,100\n"
        )
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / "ledger23_99_02.csv"
        temp_path.write_text(csv_content)

        try:
            # Create a mock player with None id for the validation result
            mock_player = Player(name="TestPlayer", flag="🏳️", putr="5.0")
            mock_player.id = None

            # Mock _validate_ledger_nicknames to return player with None id
            mock_rows = [
                {
                    "player_nickname": "TestPlayer",
                    "player_id": "id1",
                    "buy_in": "100",
                    "buy_out": "200",
                    "stack": "200",
                    "net": "100",
                }
            ]
            mock_validation_result = (mock_rows, [mock_player])

            with (
                patch(
                    "src.services.import_service._validate_ledger_nicknames",
                    return_value=mock_validation_result,
                ),
                pytest.raises(
                    ValueError,
                    match="Player ID should be populated for fetched player",
                ),
            ):
                import_single_ledger(session, temp_path)
        finally:
            temp_path.unlink()


class TestImportServiceHasLedgerEntriesBranch:
    """Test the has_ledger_entries branch in import_single_ledger."""

    def test_import_skips_when_game_has_ledger_entries(self, session, sample_player):
        """Test import returns GAME_EXISTS when game has ledger entries."""
        # Create nickname for the player
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )

        # Create game with ledger entries already
        game = Game(date_str="23_99_03", ledger_filename="ledger23_99_03.csv")
        session.add(game)
        session.flush()

        # Add a ledger entry for this game
        entry = LedgerEntry(
            game_id=game.id,
            player_id=sample_player.id,
            player_nickname=sample_player.name,
            player_id_csv="id1",
            buy_in=100.0,
            buy_out=200.0,
            stack=200.0,
            net=100.0,
        )
        session.add(entry)
        session.commit()

        # Create ledger file with same date
        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,200,200,100\n"
        )
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / "ledger23_99_03.csv"
        temp_path.write_text(csv_content)

        try:
            # Mock get_game_by_date to return None so we get past that check
            # Then has_ledger_entries will return True
            with (
                patch(
                    "src.services.import_service.get_game_by_date", return_value=None
                ),
                patch("src.services.import_service.create_game", return_value=game),
            ):
                result = import_single_ledger(session, temp_path)
                assert result == ImportResult.GAME_EXISTS
        finally:
            temp_path.unlink()


class TestImportServiceExistingStatsBranch:
    """Test the existing_stats branch in import_single_ledger."""

    def test_import_skips_creating_stats_when_they_exist(self, session, sample_player):
        """Test that existing PlayerGameStats are not duplicated during import."""
        # Create nickname for the player
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )
        session.commit()

        # Create ledger file
        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,200,200,100\n"
        )
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / "ledger23_99_04.csv"
        temp_path.write_text(csv_content)

        try:
            # Mock get_player_game_stats to return existing stats
            mock_existing_stats = PlayerGameStats(
                player_id=sample_player.id,
                game_id=1,  # Dummy game id
                net=50.0,
            )

            # Create a mock game with valid id
            mock_game = MagicMock()
            mock_game.id = 999

            with (
                patch(
                    "src.services.import_service.get_game_by_date",
                    return_value=None,
                ),
                patch(
                    "src.services.import_service.create_game",
                    return_value=mock_game,
                ),
                patch(
                    "src.services.import_service.has_ledger_entries",
                    return_value=False,
                ),
                patch(
                    "src.services.import_service.get_player_game_stats",
                    return_value=mock_existing_stats,
                ),
                patch(
                    "src.services.import_service.create_player_game_stats"
                ) as mock_create_stats,
                patch("src.services.import_service.create_ledger_entry"),
                patch("src.services.import_service.recalculate_player_stats"),
            ):
                result = import_single_ledger(session, temp_path)

                # The stats creation should NOT be called since existing_stats exists
                mock_create_stats.assert_not_called()
                assert result == ImportResult.SUCCESS
        finally:
            temp_path.unlink()


class TestPlayerStatsServicePlayerIdNone:
    """Test the player.id is None branch in recalculate_all_player_stats."""

    def test_recalculate_all_skips_player_with_none_id(self, session):
        """Test that players with None id are skipped gracefully."""
        # Create a real player
        player = Player(name="RealPlayer", flag="🏳️", putr="UR")
        session.add(player)
        session.commit()

        # Create a mock player with None id
        mock_player_with_none_id = Player(name="NoneIdPlayer", flag="🏳️", putr="UR")
        mock_player_with_none_id.id = None

        # Mock get_all_players to return list including player with None id
        with (
            patch(
                "src.services.player_stats_service.get_all_players",
                return_value=[player, mock_player_with_none_id],
            ),
            patch(
                "src.services.player_stats_service.recalculate_player_stats"
            ) as mock_recalc,
        ):
            recalculate_all_player_stats(session)

            # Should only be called for the player with valid id
            assert mock_recalc.call_count == 1
            mock_recalc.assert_called_once_with(session, player.id)


class TestImportCsvModule:
    """Test the import_csv module to cover its imports."""

    def test_import_csv_module_imports_work(self):
        """Test that the import_csv module can be imported."""
        # Simply importing the module should cover the import statements
        # Verify the module has expected attributes
        assert hasattr(src.import_csv, "logger")
