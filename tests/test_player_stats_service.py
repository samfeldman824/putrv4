"""Unit tests for player stats calculation service."""

from datetime import datetime

import pytest

from src.models.models import Game, Player, PlayerGameStats
from src.services.player_stats_service import (
    parse_date_str,
    recalculate_all_player_stats,
    recalculate_player_stats,
)


class TestParseDateStr:
    """Tests for the parse_date_str function."""

    def test_parse_simple_date(self):
        """Test parsing a simple date string."""
        result = parse_date_str("23_09_26")
        assert result == datetime(2023, 9, 26, hour=0)

    def test_parse_date_with_game_number(self):
        """Test parsing a date string with game number suffix."""
        result = parse_date_str("23_10_07(1)")
        assert result == datetime(2023, 10, 7, hour=1)

    def test_parse_date_with_game_number_2(self):
        """Test parsing a date string with higher game number."""
        result = parse_date_str("23_10_07(2)")
        assert result == datetime(2023, 10, 7, hour=2)

    def test_parse_date_ordering(self):
        """Test that dates are ordered correctly."""
        dates = ["23_09_26", "23_10_07", "23_10_07(1)", "23_10_07(2)"]
        parsed = [parse_date_str(d) for d in dates]

        assert parsed == sorted(parsed)
        assert parsed[0] < parsed[1] < parsed[2] < parsed[3]

    def test_parse_invalid_date_format(self):
        """Test that invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date_str format"):
            parse_date_str("invalid")

    def test_parse_incomplete_date(self):
        """Test that incomplete date raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date_str format"):
            parse_date_str("23_09")

    def test_parse_year_2000_offset(self):
        """Test that year is correctly offset by 2000."""
        result = parse_date_str("24_01_15")
        assert result.year == 2024


class TestRecalculatePlayerStats:
    """Tests for the recalculate_player_stats function."""

    def test_player_not_found(self, session):
        """Test handling of non-existent player."""
        # Should not raise, just log warning
        recalculate_player_stats(session, 99999)

    def test_player_with_no_games(self, session, sample_player):
        """Test stats reset when player has no games."""
        # Set some initial values
        sample_player.net = 1000.0
        sample_player.games_up = 5
        session.add(sample_player)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.expire(sample_player)

        assert sample_player.net == 0.0
        assert sample_player.games_up == 0
        assert sample_player.games_down == 0
        assert sample_player.average_net == 0.0
        assert sample_player.biggest_win == 0.0
        assert sample_player.biggest_loss == 0.0
        assert sample_player.highest_net == 0.0
        assert sample_player.lowest_net == 0.0

    def test_single_winning_game(self, session, sample_player, sample_game):
        """Test stats calculation for a single winning game."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=500.0,
        )
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.expire(sample_player)

        assert sample_player.net == 500.0
        assert sample_player.games_up == 1
        assert sample_player.games_down == 0
        assert sample_player.average_net == 500.0
        assert sample_player.biggest_win == 500.0
        assert sample_player.biggest_loss == 0.0
        assert sample_player.highest_net == 500.0
        assert sample_player.lowest_net == 0.0

    def test_single_losing_game(self, session, sample_player, sample_game):
        """Test stats calculation for a single losing game."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=-300.0,
        )
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.expire(sample_player)

        assert sample_player.net == -300.0
        assert sample_player.games_up == 0
        assert sample_player.games_down == 1
        assert sample_player.average_net == -300.0
        assert sample_player.biggest_win == 0.0
        assert sample_player.biggest_loss == -300.0
        assert sample_player.highest_net == 0.0
        assert sample_player.lowest_net == -300.0

    def test_multiple_games_total_net(self, session, player_with_game_stats):
        """Test total net calculation across multiple games."""
        recalculate_player_stats(session, player_with_game_stats.id)
        session.commit()
        session.expire(player_with_game_stats)

        # +100, -50, +200, -75, +25 = +200
        assert player_with_game_stats.net == 200.0

    def test_multiple_games_win_loss_count(self, session, player_with_game_stats):
        """Test games_up and games_down counts."""
        recalculate_player_stats(session, player_with_game_stats.id)
        session.commit()
        session.expire(player_with_game_stats)

        # Wins: +100, +200, +25 = 3
        # Losses: -50, -75 = 2
        assert player_with_game_stats.games_up == 3
        assert player_with_game_stats.games_down == 2

    def test_multiple_games_average(self, session, player_with_game_stats):
        """Test average net calculation."""
        recalculate_player_stats(session, player_with_game_stats.id)
        session.commit()
        session.expire(player_with_game_stats)

        # +200 total / 5 games = 40.0
        assert player_with_game_stats.average_net == 40.0

    def test_multiple_games_biggest_win_loss(self, session, player_with_game_stats):
        """Test biggest win and loss tracking."""
        recalculate_player_stats(session, player_with_game_stats.id)
        session.commit()
        session.expire(player_with_game_stats)

        assert player_with_game_stats.biggest_win == 200.0
        assert player_with_game_stats.biggest_loss == -75.0

    def test_rolling_highest_lowest_net(self, session, sample_player, sample_games):
        """Test rolling highest and lowest cumulative net."""
        # Create game stats that will test rolling high/low
        # Game 1: +100 (cum: 100, high: 100, low: 0)
        # Game 2: -200 (cum: -100, high: 100, low: -100)
        # Game 3: +50 (cum: -50, high: 100, low: -100)
        # Game 4: +300 (cum: 250, high: 250, low: -100)
        # Game 5: -100 (cum: 150, high: 250, low: -100)
        nets = [100.0, -200.0, 50.0, 300.0, -100.0]

        for game, net in zip(sample_games, nets, strict=True):
            stats = PlayerGameStats(
                player_id=sample_player.id,
                game_id=game.id,
                net=net,
            )
            session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.expire(sample_player)

        assert sample_player.highest_net == 250.0
        assert sample_player.lowest_net == -100.0
        assert sample_player.net == 150.0

    def test_chronological_ordering(self, session, sample_player):
        """Test that games are processed in chronological order."""
        # Create games out of order
        game1 = Game(date_str="23_10_07", ledger_filename="test1.csv")
        game2 = Game(date_str="23_09_26", ledger_filename="test2.csv")  # Earlier
        game3 = Game(
            date_str="23_10_07(1)", ledger_filename="test3.csv"
        )  # Same day, game 1
        session.add_all([game1, game2, game3])
        session.commit()

        # Add stats: order matters for rolling calculations
        # Chronological order should be: game2 (Sep 26), game1 (Oct 7), game3 (Oct 7 game 1)
        # Net values: -100 (game2), +200 (game1), -50 (game3)
        # Cumulative: -100, +100, +50
        # Highest: 100, Lowest: -100
        stats1 = PlayerGameStats(
            player_id=sample_player.id, game_id=game1.id, net=200.0
        )
        stats2 = PlayerGameStats(
            player_id=sample_player.id, game_id=game2.id, net=-100.0
        )
        stats3 = PlayerGameStats(
            player_id=sample_player.id, game_id=game3.id, net=-50.0
        )
        session.add_all([stats1, stats2, stats3])
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.expire(sample_player)

        assert sample_player.net == 50.0  # -100 + 200 - 50 = 50
        assert sample_player.highest_net == 100.0  # After game1: -100 + 200 = 100
        assert sample_player.lowest_net == -100.0  # After game2: -100


class TestRecalculateAllPlayerStats:
    """Tests for the recalculate_all_player_stats function."""

    def test_recalculate_all_players(self, session, sample_games):
        """Test that all players get their stats recalculated."""
        # Create multiple players
        player1 = Player(name="Player 1", flag="🇺🇸")
        player2 = Player(name="Player 2", flag="🇬🇧")
        session.add_all([player1, player2])
        session.commit()

        # Add game stats for both players
        stats1 = PlayerGameStats(
            player_id=player1.id, game_id=sample_games[0].id, net=100.0
        )
        stats2 = PlayerGameStats(
            player_id=player2.id, game_id=sample_games[0].id, net=-50.0
        )
        session.add_all([stats1, stats2])
        session.commit()

        recalculate_all_player_stats(session)

        session.refresh(player1)
        session.refresh(player2)

        assert player1.net == 100.0
        assert player1.games_up == 1
        assert player2.net == -50.0
        assert player2.games_down == 1

    def test_recalculate_empty_database(self, session):
        """Test recalculating when there are no players."""
        # Should not raise
        recalculate_all_player_stats(session)


class TestEdgeCases:
    """Tests for edge cases in stats calculation."""

    def test_zero_net_game(self, session, sample_player, sample_game):
        """Test that zero net game is not counted as win or loss."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=0.0,
        )
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.expire(sample_player)

        assert sample_player.net == 0.0
        assert sample_player.games_up == 0
        assert sample_player.games_down == 0
        assert sample_player.average_net == 0.0

    def test_very_large_numbers(self, session, sample_player, sample_game):
        """Test handling of large net values."""
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=1_000_000.0,
        )
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.expire(sample_player)

        assert sample_player.net == 1_000_000.0
        assert sample_player.biggest_win == 1_000_000.0

    def test_decimal_precision(self, session, sample_player, sample_games):
        """Test that decimal values are handled correctly."""
        nets = [33.33, 33.33, 33.34]  # Total: 100.00

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
        session.expire(sample_player)

        assert abs(sample_player.net - 100.0) < 0.01

    def test_putr_not_modified(self, session, sample_player, sample_game):
        """Test that PUTR value is not modified during recalculation."""
        original_putr = sample_player.putr

        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=sample_game.id,
            net=100.0,
        )
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, sample_player.id)
        session.commit()
        session.expire(sample_player)

        assert sample_player.putr == original_putr
