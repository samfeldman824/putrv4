"""Unit tests for import service."""

from pathlib import Path
import tempfile

from sqlmodel import select

from src.models.models import Game, LedgerEntry, Player, PlayerGameStats, PlayerNickname
from src.services.import_service import find_player_by_nickname, import_single_ledger


def create_temp_ledger(content: str, date_str: str = "23_11_25") -> Path:
    """Helper to create a properly named temporary ledger file."""
    temp_dir = Path(tempfile.gettempdir())
    temp_path = temp_dir / f"ledger{date_str}.csv"
    temp_path.write_text(content)
    return temp_path


class TestGetPlayerStrict:
    """Tests for the get_player_strict function."""

    def test_find_player_by_name(self, session, sample_player):
        """Test finding a player by their canonical name."""
        row = {"player_nickname": sample_player.name, "player_id": ""}

        result = find_player_by_nickname(session, row)

        assert result is not None
        assert result.id == sample_player.id
        assert result.name == sample_player.name

    def test_find_player_by_nickname(self, session, sample_player_with_nickname):
        """Test finding a player by their nickname."""
        row = {"player_nickname": "Johnny", "player_id": ""}

        result = find_player_by_nickname(session, row)

        assert result is not None
        assert result.id == sample_player_with_nickname.id
        assert result.name == "John Doe"

    def test_find_player_by_player_id_str(self, session, sample_player):
        """Test finding a player by their player_id_str."""
        # Set a player_id_str
        sample_player.player_id_str = "unique-id-123"
        session.add(sample_player)
        session.commit()

        row = {"player_nickname": "Wrong Name", "player_id": "unique-id-123"}

        result = find_player_by_nickname(session, row)

        assert result is not None
        assert result.id == sample_player.id

    def test_player_not_found_returns_none(self, session):
        """Test that non-existent player returns None."""
        row = {"player_nickname": "Unknown Player", "player_id": "unknown-id"}

        result = find_player_by_nickname(session, row)

        assert result is None

    def test_updates_player_id_str_if_missing(self, session, sample_player):
        """Test that player_id_str is updated if player found by name but missing ID."""
        assert sample_player.player_id_str is None

        row = {"player_nickname": sample_player.name, "player_id": "new-id-456"}

        result = find_player_by_nickname(session, row)
        session.refresh(sample_player)

        assert result is not None
        assert sample_player.player_id_str == "new-id-456"

    def test_does_not_update_existing_player_id_str(self, session, sample_player):
        """Test that existing player_id_str is not overwritten."""
        sample_player.player_id_str = "original-id"
        session.add(sample_player)
        session.commit()

        row = {"player_nickname": sample_player.name, "player_id": "different-id"}

        result = find_player_by_nickname(session, row)
        session.refresh(sample_player)

        assert result is not None
        # player_id_str found by name, not by ID, so it won't be updated
        # Actually, based on the code logic, it only updates if player doesn't have one
        assert sample_player.player_id_str == "original-id"

    def test_priority_player_id_over_nickname(self, session):
        """Test that player_id takes priority over nickname matching."""
        # Create two players
        player1 = Player(name="Player One", player_id_str="id-one")
        player2 = Player(name="Player Two", player_id_str="id-two")
        session.add_all([player1, player2])
        session.flush()

        # Create nickname for player2
        nickname = PlayerNickname(
            nickname="SharedNick", player_name="Player Two", player_id=player2.id
        )
        session.add(nickname)
        session.commit()

        # Search with player1's ID but player2's nickname
        row = {"player_nickname": "SharedNick", "player_id": "id-one"}

        result = find_player_by_nickname(session, row)

        # Should find player1 by ID
        assert result is not None
        assert result.id == player1.id


class TestImportSingleLedgerStrict:
    """Tests for the import_single_ledger_strict function."""

    def test_import_creates_game(self, session, sample_player):
        """Test that import creates a game record."""
        csv_content = f"player_nickname,player_id,buy_in,buy_out,stack,net\n{sample_player.name},abc123,100,200,200,100\n"
        temp_path = create_temp_ledger(csv_content, "23_11_25")

        try:
            import_single_ledger(session, temp_path)
            session.commit()

            games = session.exec(select(Game)).all()
            assert len(games) == 1
            assert games[0].date_str == "23_11_25"
        finally:
            temp_path.unlink()

    def test_import_creates_player_game_stats(self, session, sample_player):
        """Test that import creates PlayerGameStats records."""
        csv_content = f"player_nickname,player_id,buy_in,buy_out,stack,net\n{sample_player.name},abc123,100,200,200,100\n"
        temp_path = create_temp_ledger(csv_content, "23_11_26")

        try:
            import_single_ledger(session, temp_path)
            session.commit()

            stats = session.exec(
                select(PlayerGameStats).where(
                    PlayerGameStats.player_id == sample_player.id
                )
            ).all()
            assert len(stats) == 1
            assert stats[0].net == 100.0
        finally:
            temp_path.unlink()

    def test_import_creates_ledger_entry(self, session, sample_player):
        """Test that import creates LedgerEntry records."""
        csv_content = f"player_nickname,player_id,buy_in,buy_out,stack,net\n{sample_player.name},abc123,100,200,200,100\n"
        temp_path = create_temp_ledger(csv_content, "23_11_27")

        try:
            import_single_ledger(session, temp_path)
            session.commit()

            entries = session.exec(
                select(LedgerEntry).where(LedgerEntry.player_id == sample_player.id)
            ).all()
            assert len(entries) == 1
            assert entries[0].buy_in == 100.0
            assert entries[0].buy_out == 200.0
            assert entries[0].net == 100.0
            assert entries[0].player_id_csv == "abc123"
        finally:
            temp_path.unlink()

    def test_import_skips_unknown_players(self, session, sample_player):
        """Test that unknown players are skipped."""
        csv_content = f"player_nickname,player_id,buy_in,buy_out,stack,net\n{sample_player.name},abc123,100,200,200,100\nUnknown Player,xyz789,50,25,25,-25\n"
        temp_path = create_temp_ledger(csv_content, "23_11_28")

        try:
            import_single_ledger(session, temp_path)
            session.commit()

            # Should only have 1 record (known player), not 2
            stats = session.exec(select(PlayerGameStats)).all()
            assert len(stats) == 1
        finally:
            temp_path.unlink()

    def test_import_recalculates_player_stats(self, session, sample_player):
        """Test that player stats are recalculated after import."""
        csv_content = f"player_nickname,player_id,buy_in,buy_out,stack,net\n{sample_player.name},abc123,100,350,350,250\n"
        temp_path = create_temp_ledger(csv_content, "23_11_29")

        try:
            import_single_ledger(session, temp_path)
            session.commit()
            session.refresh(sample_player)

            assert sample_player.net == 250.0
            assert sample_player.games_up == 1
            assert sample_player.biggest_win == 250.0
        finally:
            temp_path.unlink()

    def test_import_multiple_players_same_game(self, session):
        """Test importing a game with multiple players."""
        player1 = Player(name="Player One", flag="🇺🇸")
        player2 = Player(name="Player Two", flag="🇬🇧")
        session.add_all([player1, player2])
        session.commit()

        csv_content = "player_nickname,player_id,buy_in,buy_out,stack,net\nPlayer One,id1,100,200,200,100\nPlayer Two,id2,100,50,50,-50\n"
        temp_path = create_temp_ledger(csv_content, "23_11_30")

        try:
            import_single_ledger(session, temp_path)
            session.commit()

            stats = session.exec(select(PlayerGameStats)).all()
            assert len(stats) == 2

            session.refresh(player1)
            session.refresh(player2)

            assert player1.net == 100.0
            assert player2.net == -50.0
        finally:
            temp_path.unlink()

    def test_import_extracts_date_from_filename(self, session, sample_player):
        """Test that date is correctly extracted from filename."""
        csv_content = f"player_nickname,player_id,buy_in,buy_out,stack,net\n{sample_player.name},abc123,100,100,100,0\n"
        temp_path = create_temp_ledger(csv_content, "24_01_15")

        try:
            import_single_ledger(session, temp_path)
            session.commit()

            game = session.exec(select(Game)).first()
            assert game is not None
            assert game.date_str == "24_01_15"
            assert game.ledger_filename == "ledger24_01_15.csv"
        finally:
            temp_path.unlink()

    def test_import_handles_empty_values(self, session, sample_player):
        """Test that empty values are handled correctly."""
        csv_content = f"player_nickname,player_id,buy_in,buy_out,stack,net,session_start_at,session_end_at\n{sample_player.name},abc123,,,,,,"
        temp_path = create_temp_ledger(csv_content, "23_12_01")

        try:
            import_single_ledger(session, temp_path)
            session.commit()

            entries = session.exec(select(LedgerEntry)).all()
            assert len(entries) == 1
            assert entries[0].buy_in == 0.0
            assert entries[0].net == 0.0
        finally:
            temp_path.unlink()
