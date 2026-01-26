"""Unit tests for game DAO."""

import pytest

from src.dao.game_dao import (
    create_game,
    create_ledger_entry,
    create_player_game_stats,
    get_game_by_date,
    get_game_by_id,
    get_player_game_stats,
    get_player_stats_with_games,
    has_ledger_entries,
)
from src.models.models import Game, LedgerEntry, PlayerGameStats


class TestGetGameById:
    """Tests for get_game_by_id."""

    def test_returns_game_when_found(self, session, sample_game):
        """Test that existing game is returned."""
        result = get_game_by_id(session, sample_game.id)
        assert result is not None
        assert result.id == sample_game.id
        assert result.date_str == sample_game.date_str

    def test_returns_none_when_not_found(self, session):
        """Test that None is returned for non-existent game."""
        result = get_game_by_id(session, 99999)
        assert result is None


class TestGetGameByDate:
    """Tests for get_game_by_date."""

    def test_returns_game_when_found(self, session, sample_game):
        """Test that existing game is returned by date."""
        result = get_game_by_date(session, sample_game.date_str)
        assert result is not None
        assert result.id == sample_game.id

    def test_returns_none_when_not_found(self, session):
        """Test that None is returned for non-existent date."""
        result = get_game_by_date(session, "99_99_99")
        assert result is None


class TestCreateGame:
    """Tests for create_game."""

    def test_flushes_and_populates_id(self, session):
        """Test that create_game flushes and populates ID."""
        game = Game(date_str="24_01_01", ledger_filename="ledger24_01_01.csv")
        assert game.id is None

        result = create_game(session, game)

        assert result.id is not None
        assert result.date_str == "24_01_01"


class TestHasLedgerEntries:
    """Tests for has_ledger_entries."""

    def test_returns_false_when_no_entries(self, session, sample_game):
        """Test that False is returned when no entries exist."""
        result = has_ledger_entries(session, sample_game.id)
        assert result is False

    def test_returns_true_when_entries_exist(self, session, sample_game, sample_player):
        """Test that True is returned when entries exist."""
        entry = LedgerEntry(
            game_id=sample_game.id,
            player_id=sample_player.id,
            player_nickname="Nick",
            player_id_csv="id",
            net=100.0,
        )
        session.add(entry)
        session.commit()

        result = has_ledger_entries(session, sample_game.id)
        assert result is True


class TestCreateLedgerEntry:
    """Tests for create_ledger_entry."""

    def test_creates_entry(self, session, sample_game, sample_player):
        """Test that ledger entry is created."""
        entry = LedgerEntry(
            game_id=sample_game.id,
            player_id=sample_player.id,
            player_nickname="TestNick",
            player_id_csv="test_id",
            buy_in=100.0,
            buy_out=200.0,
            net=100.0,
        )

        result = create_ledger_entry(session, entry)
        session.commit()

        assert result.player_nickname == "TestNick"
        assert result.net == pytest.approx(100.0)


class TestGetPlayerGameStats:
    """Tests for get_player_game_stats."""

    def test_returns_stats_when_found(self, session, sample_player, sample_game):
        """Test that existing stats are returned."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=150.0,
        )
        session.add(stats)
        session.commit()

        result = get_player_game_stats(session, sample_player.id, sample_game.id)
        assert result is not None
        assert result.net == pytest.approx(150.0)

    def test_returns_none_when_not_found(self, session, sample_player, sample_game):
        """Test that None is returned when stats don't exist."""
        result = get_player_game_stats(session, sample_player.id, sample_game.id)
        assert result is None


class TestCreatePlayerGameStats:
    """Tests for create_player_game_stats."""

    def test_creates_stats(self, session, sample_player, sample_game):
        """Test that player game stats are created."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=250.0,
        )

        result = create_player_game_stats(session, stats)
        session.commit()

        assert result.net == pytest.approx(250.0)
        assert result.player_id == sample_player.id
        assert result.game_id == sample_game.id


class TestGetPlayerStatsWithGames:
    """Tests for get_player_stats_with_games."""

    def test_returns_empty_list_when_no_stats(self, session, sample_player):
        """Test that empty list is returned when no stats exist."""
        result = get_player_stats_with_games(session, sample_player.id)
        assert result == []

    def test_returns_tuples_with_matching_ids(
        self, session, sample_player, sample_games
    ):
        """Test that tuples contain matching stat and game."""
        stats1 = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_games[0].id,
            net=100.0,
        )
        stats2 = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_games[1].id,
            net=-50.0,
        )
        session.add_all([stats1, stats2])
        session.commit()

        result = get_player_stats_with_games(session, sample_player.id)

        assert len(result) == 2
        for stat, game in result:
            assert stat.game_id == game.id
            assert stat.player_id == sample_player.id


class TestRelationshipBackPopulates:
    """Tests for relationship back-populates."""

    def test_game_player_games_populated(self, session, sample_player, sample_game):
        """Test that game.player_games is populated after adding stats."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=100.0,
        )
        session.add(stats)
        session.commit()
        session.refresh(sample_game)

        assert len(sample_game.player_games) == 1
        assert sample_game.player_games[0].net == pytest.approx(100.0)
