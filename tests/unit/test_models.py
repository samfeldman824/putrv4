"""Unit tests for database models."""

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.models import LedgerEntry, Player, PlayerGameStats, PlayerNickname


class TestPlayerModel:
    """Tests for the Player model."""

    def test_creation_with_defaults(self, session):
        """Test creating a player with default values."""
        player = Player(name="Test Player")
        session.add(player)
        session.commit()
        session.refresh(player)

        assert player.id is not None
        assert player.name == "Test Player"
        assert player.putr == "0.0"
        assert player.net == pytest.approx(0.0)
        assert player.games_up == 0
        assert player.games_down == 0
        assert player.biggest_win == pytest.approx(0.0)
        assert player.biggest_loss == pytest.approx(0.0)
        assert player.highest_net == pytest.approx(0.0)
        assert player.lowest_net == pytest.approx(0.0)
        assert player.average_net == pytest.approx(0.0)
        assert player.flag == ""

    def test_unique_name_constraint_raises(self, session, sample_player):
        """Test that duplicate player name raises IntegrityError."""
        duplicate = Player(name=sample_player.name)
        session.add(duplicate)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


class TestPlayerNicknameModel:
    """Tests for the PlayerNickname model."""

    def test_unique_nickname_constraint_raises(self, session, sample_player):
        """Test that duplicate nickname raises IntegrityError."""
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
            nickname="UniqueNick",  # Duplicate
            player_name=player2.name,
            player_id=player2.id,
        )
        session.add(nick2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


class TestPlayerNicknameRelationship:
    """Tests for Player <-> PlayerNickname relationship."""

    def test_both_sides_populated(self, session, sample_player):
        """Test that relationship populates both player.nicknames and nickname.player."""
        nickname = PlayerNickname(
            nickname="TestNick",
            player_name=sample_player.name,
            player_id=sample_player.id,
        )
        session.add(nickname)
        session.commit()
        session.refresh(sample_player)
        session.refresh(nickname)

        # Check from player side
        assert len(sample_player.nicknames) == 1
        assert sample_player.nicknames[0].nickname == "TestNick"

        # Check from nickname side
        assert nickname.player == sample_player
        assert nickname.player.name == sample_player.name


class TestPlayerGameStatsRelationship:
    """Tests for Player <-> PlayerGameStats relationship."""

    def test_both_sides_populated(self, session, sample_player, sample_game):
        """Test that relationship populates player.game_stats and stats.player."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=100.0,
        )
        session.add(stats)
        session.commit()
        session.refresh(sample_player)
        session.refresh(stats)

        # Check from player side
        assert len(sample_player.game_stats) == 1
        assert sample_player.game_stats[0].net == pytest.approx(100.0)

        # Check from stats side
        assert stats.player == sample_player


class TestGamePlayerGamesRelationship:
    """Tests for Game <-> PlayerGameStats relationship."""

    def test_both_sides_populated(self, session, sample_player, sample_game):
        """Test that relationship populates game.player_games and stats.game."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=200.0,
        )
        session.add(stats)
        session.commit()
        session.refresh(sample_game)
        session.refresh(stats)

        # Check from game side
        assert len(sample_game.player_games) == 1
        assert sample_game.player_games[0].net == pytest.approx(200.0)

        # Check from stats side
        assert stats.game == sample_game


class TestGameLedgerEntryRelationship:
    """Tests for Game <-> LedgerEntry relationship."""

    def test_both_sides_populated(self, session, sample_player, sample_game):
        """Test that relationship populates game.ledger_entries and entry.game."""
        entry = LedgerEntry(
            game_id=sample_game.id,
            player_id=sample_player.id,
            player_nickname="TestNick",
            player_id_csv="test_id",
            net=150.0,
        )
        session.add(entry)
        session.commit()
        session.refresh(sample_game)
        session.refresh(entry)

        # Check from game side
        assert len(sample_game.ledger_entries) == 1
        assert sample_game.ledger_entries[0].net == pytest.approx(150.0)

        # Check from entry side
        assert entry.game == sample_game
