"""Unit tests for database models."""

import pytest

from src.models import Game, LedgerEntry, Player, PlayerGameStats, PlayerNickname


class TestPlayerModel:
    """Tests for the Player model."""

    def test_create_player(self, session):
        """Test creating a player with default values."""
        player = Player(name="Test Player")
        session.add(player)
        session.commit()
        session.refresh(player)

        assert player.id is not None
        assert player.name == "Test Player"
        assert player.flag == ""
        assert player.putr == "0.0"
        assert player.net == 0.0
        assert player.games_up == 0
        assert player.games_down == 0

    def test_create_player_with_all_fields(self, session):
        """Test creating a player with all fields populated."""
        player = Player(
            name="Full Player",
            flag="🇺🇸",
            putr="7.5",
            player_id_str="abc-123",
            net=1000.0,
            biggest_win=500.0,
            biggest_loss=-300.0,
            highest_net=1200.0,
            lowest_net=-100.0,
            games_up=10,
            games_down=5,
            average_net=66.67,
        )
        session.add(player)
        session.commit()
        session.refresh(player)

        assert player.putr == "7.5"
        assert player.net == 1000.0
        assert player.games_up == 10

    def test_player_unique_name(self, session):
        """Test that player names must be unique."""
        player1 = Player(name="Duplicate")
        session.add(player1)
        session.commit()

        player2 = Player(name="Duplicate")
        session.add(player2)

        with pytest.raises(Exception):  # IntegrityError
            session.commit()

    def test_player_putr_can_be_ur(self, session):
        """Test that PUTR can be 'UR' (unrated)."""
        player = Player(name="Unrated Player", putr="UR")
        session.add(player)
        session.commit()
        session.refresh(player)

        assert player.putr == "UR"


class TestPlayerNicknameModel:
    """Tests for the PlayerNickname model."""

    def test_create_nickname(self, session, sample_player):
        """Test creating a nickname for a player."""
        nickname = PlayerNickname(
            nickname="TestNick",
            player_name=sample_player.name,
            player_id=sample_player.id,
        )
        session.add(nickname)
        session.commit()
        session.refresh(nickname)

        assert nickname.id is not None
        assert nickname.nickname == "TestNick"
        assert nickname.player_id == sample_player.id

    def test_nickname_player_relationship(self, session, sample_player_with_nickname):
        """Test the relationship between nickname and player."""
        session.refresh(sample_player_with_nickname)

        assert len(sample_player_with_nickname.nicknames) == 1
        assert sample_player_with_nickname.nicknames[0].nickname == "Johnny"
        assert (
            sample_player_with_nickname.nicknames[0].player
            == sample_player_with_nickname
        )

    def test_nickname_unique(self, session, sample_player):
        """Test that nicknames must be unique."""
        nick1 = PlayerNickname(
            nickname="UniqueNick",
            player_name=sample_player.name,
            player_id=sample_player.id,
        )
        session.add(nick1)
        session.commit()

        # Create another player
        player2 = Player(name="Another Player")
        session.add(player2)
        session.commit()

        nick2 = PlayerNickname(
            nickname="UniqueNick", player_name=player2.name, player_id=player2.id
        )
        session.add(nick2)

        with pytest.raises(Exception):  # IntegrityError
            session.commit()


class TestGameModel:
    """Tests for the Game model."""

    def test_create_game(self, session):
        """Test creating a game."""
        game = Game(date_str="23_10_07", ledger_filename="ledger23_10_07.csv")
        session.add(game)
        session.commit()
        session.refresh(game)

        assert game.id is not None
        assert game.date_str == "23_10_07"
        assert game.ledger_filename == "ledger23_10_07.csv"

    def test_create_game_with_suffix(self, session):
        """Test creating a game with date suffix for multiple games same day."""
        game = Game(date_str="23_10_07(1)", ledger_filename="ledger23_10_07(1).csv")
        session.add(game)
        session.commit()
        session.refresh(game)

        assert game.date_str == "23_10_07(1)"

    def test_game_without_ledger_filename(self, session):
        """Test creating a game without ledger filename."""
        game = Game(date_str="23_10_07")
        session.add(game)
        session.commit()
        session.refresh(game)

        assert game.ledger_filename is None


class TestPlayerGameStatsModel:
    """Tests for the PlayerGameStats model."""

    def test_create_player_game_stats(self, session, sample_player, sample_game):
        """Test creating player game stats."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=250.0,
        )
        session.add(stats)
        session.commit()
        session.refresh(stats)

        assert stats.id is not None
        assert stats.net == 250.0
        assert stats.player_id == sample_player.id
        assert stats.game_id == sample_game.id

    def test_player_game_stats_relationships(self, session, sample_player, sample_game):
        """Test the relationships in PlayerGameStats."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=100.0,
        )
        session.add(stats)
        session.commit()
        session.refresh(stats)

        assert stats.player == sample_player
        assert stats.game == sample_game

    def test_player_game_stats_from_player(self, session, sample_player, sample_game):
        """Test accessing game stats from player."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=100.0,
        )
        session.add(stats)
        session.commit()
        session.refresh(sample_player)

        assert len(sample_player.game_stats) == 1
        assert sample_player.game_stats[0].net == 100.0

    def test_negative_net(self, session, sample_player, sample_game):
        """Test creating stats with negative net."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=-500.0,
        )
        session.add(stats)
        session.commit()
        session.refresh(stats)

        assert stats.net == -500.0


class TestLedgerEntryModel:
    """Tests for the LedgerEntry model."""

    def test_create_ledger_entry(self, session, sample_player, sample_game):
        """Test creating a ledger entry."""
        entry = LedgerEntry(
            game_id=sample_game.id,
            player_id=sample_player.id,
            player_nickname="TestNick",
            player_id_csv="abc-123",
            buy_in=100.0,
            buy_out=200.0,
            stack=200.0,
            net=100.0,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)

        assert entry.id is not None
        assert entry.buy_in == 100.0
        assert entry.net == 100.0

    def test_ledger_entry_with_session_times(self, session, sample_player, sample_game):
        """Test ledger entry with session start and end times."""
        entry = LedgerEntry(
            game_id=sample_game.id,
            player_id=sample_player.id,
            player_nickname="Test",
            player_id_csv="xyz",
            session_start_at="2023-10-07T18:00:00Z",
            session_end_at="2023-10-07T23:00:00Z",
            buy_in=100.0,
            buy_out=150.0,
            stack=150.0,
            net=50.0,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)

        assert entry.session_start_at == "2023-10-07T18:00:00Z"
        assert entry.session_end_at == "2023-10-07T23:00:00Z"

    def test_ledger_entry_relationships(self, session, sample_player, sample_game):
        """Test ledger entry relationships."""
        entry = LedgerEntry(
            game_id=sample_game.id,
            player_id=sample_player.id,
            player_nickname="Test",
            player_id_csv="xyz",
            net=100.0,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)

        assert entry.game == sample_game
        assert entry.player == sample_player
