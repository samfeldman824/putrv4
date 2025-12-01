"""Unit tests for player stats calculation service."""

import pytest

from src.models.models import Game, PlayerGameStats
from src.services.player_stats_service import (
    parse_date_str,
    recalculate_player_stats,
)


class TestParseDateStr:
    """Tests for parse_date_str."""

    def test_parses_simple_date(self):
        """Test parsing a simple date string."""
        result = parse_date_str("23_09_26")
        assert result.year == 2023
        assert result.month == 9
        assert result.day == 26
        assert result.hour == 0

    def test_same_day_suffix_ordering(self):
        """Test that same-day suffixes are ordered correctly."""
        base = parse_date_str("23_10_07")
        first = parse_date_str("23_10_07(1)")
        second = parse_date_str("23_10_07(2)")

        assert base < first < second
        assert base.hour == 0
        assert first.hour == 1
        assert second.hour == 2

    def test_invalid_format_raises_value_error(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date_str format"):
            parse_date_str("invalid")

    def test_incomplete_date_raises_value_error(self):
        """Test that incomplete date raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date_str format"):
            parse_date_str("23_09")


class TestRecalculatePlayerStats:
    """Tests for recalculate_player_stats."""

    def test_player_not_found_no_error(self, session):
        """Test that non-existent player doesn't raise error."""
        # Should log warning but not raise
        recalculate_player_stats(session, 99999)

    def test_no_games_resets_stats_to_zero(self, session, sample_player):
        """Test that player with no games has stats reset to zero."""
        # Set some initial values
        sample_player.net = 1000.0
        sample_player.games_up = 5
        sample_player.games_down = 3
        session.add(sample_player)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.net == pytest.approx(0.0)
        assert sample_player.games_up == 0
        assert sample_player.games_down == 0
        assert sample_player.average_net == pytest.approx(0.0)
        assert sample_player.biggest_win == pytest.approx(0.0)
        assert sample_player.biggest_loss == pytest.approx(0.0)
        assert sample_player.highest_net == pytest.approx(0.0)
        assert sample_player.lowest_net == pytest.approx(0.0)

    def test_single_winning_game(self, session, sample_player, sample_game):
        """Test stats for a single winning game."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=500.0,
        )
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.net == pytest.approx(500.0)
        assert sample_player.games_up == 1
        assert sample_player.games_down == 0
        assert sample_player.average_net == pytest.approx(500.0)
        assert sample_player.biggest_win == pytest.approx(500.0)
        assert sample_player.biggest_loss == pytest.approx(0.0)
        assert sample_player.highest_net == pytest.approx(500.0)
        assert sample_player.lowest_net == pytest.approx(0.0)

    def test_single_losing_game(self, session, sample_player, sample_game):
        """Test stats for a single losing game."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=-300.0,
        )
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.net == pytest.approx(-300.0)
        assert sample_player.games_up == 0
        assert sample_player.games_down == 1
        assert sample_player.average_net == pytest.approx(-300.0)
        assert sample_player.biggest_win == pytest.approx(0.0)
        assert sample_player.biggest_loss == pytest.approx(-300.0)
        assert sample_player.highest_net == pytest.approx(0.0)
        assert sample_player.lowest_net == pytest.approx(-300.0)

    def test_zero_net_game_not_counted_as_win_or_loss(
        self, session, sample_player, sample_game
    ):
        """Test that zero-net game doesn't count as win or loss."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=0.0,
        )
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.net == pytest.approx(0.0)
        assert sample_player.games_up == 0
        assert sample_player.games_down == 0
        assert sample_player.average_net == pytest.approx(0.0)

    def test_all_games_zero_net(self, session, sample_player, sample_games):
        """Test that all zero-net games keeps counts at zero."""
        for game in sample_games[:3]:
            stats = PlayerGameStats(
                player_id=sample_player.id,
                game_id=game.id,
                net=0.0,
            )
            session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.net == pytest.approx(0.0)
        assert sample_player.games_up == 0
        assert sample_player.games_down == 0
        assert sample_player.average_net == pytest.approx(0.0)
        assert sample_player.biggest_win == pytest.approx(0.0)
        assert sample_player.biggest_loss == pytest.approx(0.0)

    def test_multiple_games_calculates_correctly(
        self, session, sample_player, sample_games
    ):
        """Test total, average, and counts for multiple games."""
        # +100, -50, +200 = +250 total
        nets = [100.0, -50.0, 200.0]
        for game, net in zip(sample_games[:3], nets, strict=True):
            stats = PlayerGameStats(
                player_id=sample_player.id,
                game_id=game.id,
                net=net,
            )
            session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.net == pytest.approx(250.0)
        assert sample_player.games_up == 2
        assert sample_player.games_down == 1
        assert sample_player.average_net == pytest.approx(250.0 / 3)
        assert sample_player.biggest_win == pytest.approx(200.0)
        assert sample_player.biggest_loss == pytest.approx(-50.0)

    def test_rolling_high_low_when_first_game_negative(self, session, sample_player):
        """Test rolling high/low when first game is negative."""
        # Create games in chronological order
        game1 = Game(date_str="23_01_01", ledger_filename="g1.csv")
        game2 = Game(date_str="23_02_01", ledger_filename="g2.csv")
        game3 = Game(date_str="23_03_01", ledger_filename="g3.csv")
        session.add_all([game1, game2, game3])
        session.commit()

        # Game 1: -100 (cum: -100, low: -100, high: 0)
        # Game 2: +200 (cum: +100, low: -100, high: 100)
        # Game 3: -50  (cum: +50,  low: -100, high: 100)
        session.add(
            PlayerGameStats(player_id=sample_player.id, game_id=game1.id, net=-100.0)
        )
        session.add(
            PlayerGameStats(player_id=sample_player.id, game_id=game2.id, net=200.0)
        )
        session.add(
            PlayerGameStats(player_id=sample_player.id, game_id=game3.id, net=-50.0)
        )
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.net == pytest.approx(50.0)
        assert sample_player.highest_net == pytest.approx(100.0)
        assert sample_player.lowest_net == pytest.approx(-100.0)

    def test_chronological_ordering_with_same_day_suffixes(
        self, session, sample_player
    ):
        """Test that same-day suffixes affect rolling high/low correctly."""
        # Create games out of order by ID but with same-day suffixes
        game_base = Game(date_str="23_10_07", ledger_filename="base.csv")
        game_suffix1 = Game(date_str="23_10_07(1)", ledger_filename="s1.csv")
        game_suffix2 = Game(date_str="23_10_07(2)", ledger_filename="s2.csv")
        session.add_all([game_suffix2, game_base, game_suffix1])  # Add out of order
        session.commit()

        # Chronological order: base(+100) -> (1)(-200) -> (2)(+150)
        # Cumulative: 100, -100, 50
        # Highest: 100, Lowest: -100
        session.add(
            PlayerGameStats(player_id=sample_player.id, game_id=game_base.id, net=100.0)
        )
        session.add(
            PlayerGameStats(
                player_id=sample_player.id, game_id=game_suffix1.id, net=-200.0
            )
        )
        session.add(
            PlayerGameStats(
                player_id=sample_player.id, game_id=game_suffix2.id, net=150.0
            )
        )
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.net == pytest.approx(50.0)
        assert sample_player.highest_net == pytest.approx(100.0)
        assert sample_player.lowest_net == pytest.approx(-100.0)

    def test_does_not_mutate_putr(self, session, sample_player, sample_game):
        """Test that PUTR is not modified during recalculation."""
        original_putr = sample_player.putr
        assert original_putr == "5.0"

        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=1000.0,
        )
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.putr == original_putr
