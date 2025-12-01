"""Unit tests for import service."""

from pathlib import Path
import tempfile

import pytest
from sqlmodel import select

from src.dao.player_dao import create_nickname
from src.models.models import Game, LedgerEntry, PlayerGameStats, PlayerNickname
from src.services.import_service import (
    ImportResult,
    import_single_ledger,
)


def create_temp_ledger(content: str, date_str: str = "23_11_25") -> Path:
    """Helper to create a properly named temporary ledger file."""
    temp_dir = Path(tempfile.gettempdir())
    temp_path = temp_dir / f"ledger{date_str}.csv"
    temp_path.write_text(content)
    return temp_path


class TestImportSingleLedger:
    """Tests for import_single_ledger."""

    def test_missing_nickname_returns_missing_nicknames(self, session, sample_player):
        """Test that any missing nickname aborts with MISSING_NICKNAMES."""
        # Create nickname for sample_player
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )
        session.commit()

        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,200,200,100\n"
            "UnknownPlayer,id2,50,25,25,-25\n"  # This one doesn't exist
        )
        temp_path = create_temp_ledger(csv_content, "23_12_01")

        try:
            result = import_single_ledger(session, temp_path)
            assert result == ImportResult.MISSING_NICKNAMES
        finally:
            temp_path.unlink()

    def test_game_already_exists_returns_game_exists(self, session, sample_player):
        """Test that duplicate game returns GAME_EXISTS."""
        # Create nickname
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )
        # Create existing game with same date
        game = Game(date_str="23_12_02", ledger_filename="ledger23_12_02.csv")
        session.add(game)
        session.commit()

        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,200,200,100\n"
        )
        temp_path = create_temp_ledger(csv_content, "23_12_02")

        try:
            result = import_single_ledger(session, temp_path)
            assert result == ImportResult.GAME_EXISTS
        finally:
            temp_path.unlink()

    def test_ledger_entries_exist_returns_game_exists(self, session, sample_player):
        """Test that pre-existing ledger entries returns GAME_EXISTS."""
        # Create nickname
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )
        session.commit()

        # First import
        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,200,200,100\n"
        )
        temp_path = create_temp_ledger(csv_content, "23_12_03")

        try:
            result1 = import_single_ledger(session, temp_path)
            session.commit()
            assert result1 == ImportResult.SUCCESS

            # Second import of same file should return GAME_EXISTS
            result2 = import_single_ledger(session, temp_path)
            assert result2 == ImportResult.GAME_EXISTS
        finally:
            temp_path.unlink()

    def test_successful_import_creates_records(self, session, sample_player):
        """Test that successful import creates Game, PlayerGameStats, LedgerEntry."""
        # Create nickname
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )
        session.commit()

        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,300,300,200\n"
        )
        temp_path = create_temp_ledger(csv_content, "23_12_04")

        try:
            result = import_single_ledger(session, temp_path)
            session.commit()

            assert result == ImportResult.SUCCESS

            # Check Game was created
            games = session.exec(select(Game)).all()
            assert len(games) == 1
            assert games[0].date_str == "23_12_04"

            # Check PlayerGameStats was created
            stats = session.exec(select(PlayerGameStats)).all()
            assert len(stats) == 1
            assert stats[0].net == pytest.approx(200.0)

            # Check LedgerEntry was created
            entries = session.exec(select(LedgerEntry)).all()
            assert len(entries) == 1
            assert entries[0].buy_in == pytest.approx(100.0)
            assert entries[0].buy_out == pytest.approx(300.0)
        finally:
            temp_path.unlink()

    def test_import_recalculates_player_stats(self, session, sample_player):
        """Test that player stats are recalculated after import."""
        # Create nickname
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )
        session.commit()

        assert sample_player.net == pytest.approx(0.0)

        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,350,350,250\n"
        )
        temp_path = create_temp_ledger(csv_content, "23_12_05")

        try:
            result = import_single_ledger(session, temp_path)
            session.commit()
            session.refresh(sample_player)

            assert result == ImportResult.SUCCESS
            assert sample_player.net == pytest.approx(250.0)
            assert sample_player.games_up == 1
            assert sample_player.biggest_win == pytest.approx(250.0)
        finally:
            temp_path.unlink()
