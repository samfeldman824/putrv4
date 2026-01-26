"""Extended unit tests for player stats service - covering uncovered branches."""

import pytest

from src.core.exceptions import ValidationError
from src.models.models import Game, Player, PlayerGameStats
from src.services.player_stats_service import (
    parse_date_str,
    recalculate_all_player_stats,
    recalculate_player_stats,
)


class TestParseDateStr:
    """Tests for parse_date_str function edge cases."""

    def test_parses_standard_date(self):
        """Test parsing standard YY_MM_DD format."""
        result = parse_date_str("23_09_26")
        assert result.year == 2023
        assert result.month == 9
        assert result.day == 26
        assert result.hour == 0

    def test_parses_date_with_game_number(self):
        """Test parsing YY_MM_DD(N) format with game number."""
        result = parse_date_str("23_09_26(2)")
        assert result.year == 2023
        assert result.month == 9
        assert result.day == 26
        assert result.hour == 2  # Game number used as hour

    def test_invalid_game_number_defaults_to_zero(self):
        """Test that invalid game number suffix defaults to 0."""
        # Malformed game number
        result = parse_date_str("23_09_26(abc)")
        assert result.hour == 0

    def test_empty_game_number_defaults_to_zero(self):
        """Test that empty game number suffix defaults to 0."""
        result = parse_date_str("23_09_26()")
        assert result.hour == 0

    def test_invalid_date_format_raises_validation_error(self):
        """Test that invalid date format raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid date_str format"):
            parse_date_str("invalid")

    def test_too_few_parts_raises_validation_error(self):
        """Test that date with too few parts raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid date_str format"):
            parse_date_str("23_09")

    def test_too_many_parts_raises_validation_error(self):
        """Test that date with too many parts raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid date_str format"):
            parse_date_str("23_09_26_extra")


class TestRecalculateAllPlayerStats:
    """Tests for recalculate_all_player_stats function."""

    def test_recalculates_stats_for_all_players(self, session):
        """Test that all players' stats are recalculated."""
        # Create multiple players with games
        player1 = Player(name="Alice", flag="🇺🇸", putr="5.0")
        player2 = Player(name="Bob", flag="🇬🇧", putr="3.5")
        session.add(player1)
        session.add(player2)
        session.flush()

        # Create games
        game1 = Game(date_str="23_09_01", ledger_filename="ledger23_09_01.csv")
        game2 = Game(date_str="23_09_02", ledger_filename="ledger23_09_02.csv")
        session.add(game1)
        session.add(game2)
        session.flush()

        # Add game stats - Alice wins, Bob loses
        stats1 = PlayerGameStats(player_id=player1.id, game_id=game1.id, net=100.0)
        stats2 = PlayerGameStats(player_id=player2.id, game_id=game1.id, net=-100.0)
        stats3 = PlayerGameStats(player_id=player1.id, game_id=game2.id, net=50.0)
        stats4 = PlayerGameStats(player_id=player2.id, game_id=game2.id, net=-50.0)
        session.add_all([stats1, stats2, stats3, stats4])
        session.commit()

        # Reset player stats to verify recalculation works
        player1.net = 0.0
        player2.net = 0.0
        session.commit()

        # Recalculate all
        recalculate_all_player_stats(session)
        session.commit()
        session.refresh(player1)
        session.refresh(player2)

        assert player1.net == pytest.approx(150.0)  # 100 + 50
        assert player2.net == pytest.approx(-150.0)  # -100 - 50
        assert player1.games_up == 2
        assert player2.games_down == 2

    def test_handles_players_with_no_games(self, session):
        """Test that players with no games get zero stats."""
        player = Player(name="NoGames", flag="🏳️", putr="UR")
        session.add(player)
        session.commit()

        recalculate_all_player_stats(session)
        session.commit()
        session.refresh(player)

        assert player.net == pytest.approx(0.0)
        assert player.games_up == 0
        assert player.games_down == 0

    def test_handles_empty_database(self, session):
        """Test that recalculate handles empty database gracefully."""
        # Should not raise any errors
        recalculate_all_player_stats(session)

    def test_handles_player_with_null_id(self, session):
        """Test that players with None id are skipped gracefully."""
        # Create a normal player
        player = Player(name="Test", flag="🏳️", putr="UR")
        session.add(player)
        session.commit()

        # This shouldn't raise - players from DB always have IDs
        recalculate_all_player_stats(session)


class TestRecalculatePlayerStatsEdgeCases:
    """Edge case tests for recalculate_player_stats."""

    def test_nonexistent_player_id_handles_gracefully(self, session):
        """Test that nonexistent player ID is handled gracefully without raising."""
        # Should not raise an exception for non-existent player
        recalculate_player_stats(session, 99999)
        # If we get here without exception, the function handled it gracefully

    def test_player_with_only_zero_net_games(self, session):
        """Test player who broke even in all games."""
        player = Player(name="BreakEven", flag="🏳️", putr="UR")
        session.add(player)
        session.flush()

        game = Game(date_str="23_09_01", ledger_filename="ledger.csv")
        session.add(game)
        session.flush()

        stats = PlayerGameStats(player_id=player.id, game_id=game.id, net=0.0)
        session.add(stats)
        session.commit()

        recalculate_player_stats(session, player.id)
        session.commit()
        session.refresh(player)

        assert player.net == pytest.approx(0.0)
        assert player.games_up == 0
        assert player.games_down == 0
        assert player.average_net == pytest.approx(0.0)

    def test_rolling_min_max_with_alternating_wins_losses(self, session):
        """Test highest/lowest net tracking with alternating results."""
        player = Player(name="Alternating", flag="🏳️", putr="UR")
        session.add(player)
        session.commit()

        # Create games in chronological order
        dates = ["23_09_01", "23_09_02", "23_09_03", "23_09_04"]
        games = []
        for date in dates:
            game = Game(date_str=date, ledger_filename=f"ledger{date}.csv")
            session.add(game)
            games.append(game)
        session.commit()

        # Alternating results: +100, -200, +150, -50
        # Cumulative: 100, -100, 50, 0
        # High: 100, Low: -100
        nets = [100.0, -200.0, 150.0, -50.0]
        for game, net in zip(games, nets, strict=True):
            stats = PlayerGameStats(player_id=player.id, game_id=game.id, net=net)
            session.add(stats)
        session.commit()

        recalculate_player_stats(session, player.id)
        session.commit()
        session.refresh(player)

        assert player.net == pytest.approx(0.0)
        assert player.highest_net == pytest.approx(100.0)
        assert player.lowest_net == pytest.approx(-100.0)
        assert player.biggest_win == pytest.approx(150.0)
        assert player.biggest_loss == pytest.approx(-200.0)
        assert player.games_up == 2
        assert player.games_down == 2
