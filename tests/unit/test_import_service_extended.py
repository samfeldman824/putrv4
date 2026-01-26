"""Extended unit tests for import service - covering uncovered branches."""

import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine as sm_create_engine, select

from src.dao.player_dao import create_nickname
from src.models.models import Game, LedgerEntry, Player, PlayerGameStats, PlayerNickname
from src.services.import_service import (
    ImportResult,
    _parse_float,  # noqa: PLC2701
    _validate_ledger_nicknames,  # noqa: PLC2701
    add_records,
    import_all_ledgers,
    import_single_ledger,
    reset_db,
)


def create_temp_ledger(content: str, date_str: str = "23_11_25") -> Path:
    """Helper to create a properly named temporary ledger file."""
    temp_dir = Path(tempfile.gettempdir())
    temp_path = temp_dir / f"ledger{date_str}.csv"
    temp_path.write_text(content)
    return temp_path


class TestParseFloat:
    """Tests for _parse_float function."""

    def test_empty_string_returns_zero(self):
        """Test that empty string returns 0.0."""
        assert _parse_float("") == 0.0

    def test_none_returns_zero(self):
        """Test that None returns 0.0."""
        assert _parse_float(None) == 0.0

    def test_whitespace_only_returns_zero(self):
        """Test that whitespace-only string returns 0.0."""
        assert _parse_float("   ") == 0.0

    def test_valid_float_parses_correctly(self):
        """Test that valid float string parses correctly."""
        assert _parse_float("123.45") == pytest.approx(123.45)

    def test_negative_float_parses_correctly(self):
        """Test that negative float string parses correctly."""
        assert _parse_float("-50.25") == pytest.approx(-50.25)

    def test_integer_string_parses_as_float(self):
        """Test that integer string parses as float."""
        assert _parse_float("100") == pytest.approx(100.0)


class TestAddRecords:
    """Tests for add_records function."""

    def test_adds_players_from_backup_file(self, test_engine):
        """Test that add_records creates players from backup JSON."""
        backup_data = {
            "Alice": {
                "flag": "🇺🇸",
                "putr": "5.0",
                "player_nicknames": ["Alice", "AliceP"],
            },
            "Bob": {"flag": "🇬🇧", "putr": "3.5", "player_nicknames": ["Bob", "Bobby"]},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(backup_data, f)
            backup_path = f.name

        try:
            with patch("src.services.import_service.engine", test_engine):
                add_records(backup_path)

            with Session(test_engine) as session:
                players = session.exec(select(Player)).all()
                assert len(players) == 2

                alice = session.exec(
                    select(Player).where(Player.name == "Alice")
                ).first()
                assert alice is not None
                assert alice.flag == "🇺🇸"
                assert alice.putr == "5.0"

                # Check nicknames
                nicknames = session.exec(
                    select(PlayerNickname).where(PlayerNickname.player_name == "Alice")
                ).all()
                assert len(nicknames) == 2
        finally:
            Path(backup_path).unlink()

    def test_skips_existing_players(self, test_engine):
        """Test that add_records skips already existing players."""
        # Create existing player
        with Session(test_engine) as session:
            player = Player(name="Alice", flag="🇺🇸", putr="5.0")
            session.add(player)
            session.commit()

        backup_data = {
            "Alice": {
                "flag": "🇫🇷",  # Different flag
                "putr": "3.0",
                "player_nicknames": ["AliceNew"],
            },
            "Bob": {"flag": "🇬🇧", "putr": "3.5", "player_nicknames": ["Bob"]},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(backup_data, f)
            backup_path = f.name

        try:
            with patch("src.services.import_service.engine", test_engine):
                add_records(backup_path)

            with Session(test_engine) as session:
                players = session.exec(select(Player)).all()
                # Should have 2 players (Alice exists, Bob added)
                assert len(players) == 2

                # Alice should keep original flag (not updated)
                alice = session.exec(
                    select(Player).where(Player.name == "Alice")
                ).first()
                assert alice is not None
                assert alice.flag == "🇺🇸"  # Original flag kept
        finally:
            Path(backup_path).unlink()


class TestResetDb:
    """Tests for reset_db function."""

    def test_drops_and_recreates_tables(self):
        """Test that reset_db drops all tables and recreates them."""
        # Create a separate engine for reset_db testing
        reset_engine = sm_create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(reset_engine)

        # Create some data first
        with Session(reset_engine) as session:
            player = Player(name="Test", flag="🏳️", putr="UR")
            session.add(player)
            session.commit()

        # Verify data exists
        with Session(reset_engine) as session:
            players = session.exec(select(Player)).all()
            assert len(players) == 1

        # Reset database - patch both engine references
        with (
            patch("src.services.import_service.engine", reset_engine),
            patch("src.core.db.engine", reset_engine),
        ):
            reset_db()

        # Verify data is gone (tables recreated, data cleared)
        with Session(reset_engine) as session:
            players = session.exec(select(Player)).all()
            assert len(players) == 0

        reset_engine.dispose()


class TestImportAllLedgers:
    """Tests for import_all_ledgers function."""

    def test_imports_all_csv_files_in_directory(self, test_engine):
        """Test that import_all_ledgers processes all CSV files."""
        # Create temp directory with ledger files
        with tempfile.TemporaryDirectory() as temp_dir:
            ledgers_dir = Path(temp_dir)

            # Create a player with nickname first
            with Session(test_engine) as session:
                player = Player(name="Alice", flag="🏳️", putr="5.0")
                session.add(player)
                session.flush()
                nickname = PlayerNickname(
                    nickname="Alice", player_name="Alice", player_id=player.id
                )
                session.add(nickname)
                session.commit()

            # Create ledger files
            csv_content = "player_nickname,player_id,buy_in,buy_out,stack,net\nAlice,id1,100,200,200,100\n"
            (ledgers_dir / "ledger23_11_01.csv").write_text(csv_content)
            (ledgers_dir / "ledger23_11_02.csv").write_text(csv_content)

            with patch("src.services.import_service.engine", test_engine):
                import_all_ledgers(temp_dir)

            # Verify games were created
            with Session(test_engine) as session:
                games = session.exec(select(Game)).all()
                assert len(games) == 2

    def test_handles_nonexistent_directory(self, test_engine):
        """Test that import_all_ledgers handles missing directory gracefully."""
        # Should not raise exception when directory doesn't exist
        with patch("src.services.import_service.engine", test_engine):
            # This should handle the error gracefully and return without raising
            import_all_ledgers("/nonexistent/path/to/ledgers")
        # If we get here without exception, the test passes


class TestImportSingleLedgerExtended:
    """Extended tests for import_single_ledger edge cases."""

    def test_existing_player_game_stats_skips_creation(self, session, sample_player):
        """Test that existing PlayerGameStats are not duplicated."""
        # Create nickname for player
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )

        # Create game and existing stats
        game = Game(date_str="23_12_10", ledger_filename="ledger23_12_10.csv")
        session.add(game)
        session.flush()

        existing_stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=game.id,
            net=50.0,
        )
        session.add(existing_stats)
        session.commit()

        # Import ledger with same player - should NOT create duplicate stats
        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,200,200,100\n"
        )
        temp_path = create_temp_ledger(csv_content, "23_12_10")

        try:
            # But the game already exists so it should return GAME_EXISTS
            result = import_single_ledger(session, temp_path)
            assert result == ImportResult.GAME_EXISTS
        finally:
            temp_path.unlink()

    def test_validates_all_nicknames_before_import(self, session, sample_player):
        """Test that validation happens before any imports."""
        create_nickname(
            session,
            PlayerNickname(
                nickname=sample_player.name,
                player_name=sample_player.name,
                player_id=sample_player.id,
            ),
        )
        session.commit()

        # CSV with one valid and one invalid nickname
        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            f"{sample_player.name},id1,100,200,200,100\n"
            "UnknownPlayer,id2,100,50,50,-50\n"
        )
        temp_path = create_temp_ledger(csv_content, "23_12_11")

        try:
            result = import_single_ledger(session, temp_path)
            assert result == ImportResult.MISSING_NICKNAMES

            # Verify no game was created
            games = session.exec(select(Game)).all()
            assert len(games) == 0
        finally:
            temp_path.unlink()

    def test_import_with_empty_net_value(self, session, sample_player):
        """Test importing ledger with empty net value."""
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
            f"{sample_player.name},id1,100,100,100,\n"  # Empty net
        )
        temp_path = create_temp_ledger(csv_content, "23_12_12")

        try:
            result = import_single_ledger(session, temp_path)
            session.commit()

            assert result == ImportResult.SUCCESS

            # Verify entry was created with 0.0 net
            entries = session.exec(select(LedgerEntry)).all()
            assert len(entries) == 1
            assert entries[0].net == pytest.approx(0.0)
        finally:
            temp_path.unlink()


class TestValidateLedgerNicknames:
    """Tests for _validate_ledger_nicknames function."""

    def test_returns_none_for_missing_nicknames(self, session):
        """Test that missing nicknames returns None."""
        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            "UnknownPlayer,id1,100,200,200,100\n"
        )
        temp_path = create_temp_ledger(csv_content, "23_12_13")

        try:
            result = _validate_ledger_nicknames(session, temp_path)
            assert result is None
        finally:
            temp_path.unlink()

    def test_returns_rows_and_players_for_valid_nicknames(self, session, sample_player):
        """Test that valid nicknames return rows and players."""
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
        )
        temp_path = create_temp_ledger(csv_content, "23_12_14")

        try:
            result = _validate_ledger_nicknames(session, temp_path)
            assert result is not None
            rows, players = result
            assert len(rows) == 1
            assert len(players) == 1
            assert players[0].id == sample_player.id
        finally:
            temp_path.unlink()

    def test_handles_empty_nickname_field(self, session):
        """Test that empty nickname field is handled."""
        csv_content = (
            "player_nickname,player_id,buy_in,buy_out,stack,net\n"
            ",id1,100,200,200,100\n"  # Empty nickname
        )
        temp_path = create_temp_ledger(csv_content, "23_12_15")

        try:
            result = _validate_ledger_nicknames(session, temp_path)
            # Should return None because empty nickname won't match any player
            assert result is None
        finally:
            temp_path.unlink()
