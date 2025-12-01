"""Unit tests for player DAO."""

import pytest
from sqlalchemy.exc import IntegrityError

from src.dao.player_dao import (
    create_nickname,
    create_player,
    get_all_players,
    get_player_by_id,
    get_player_by_name,
    get_player_by_nickname,
    update_player,
)
from src.models.models import Player, PlayerNickname


class TestGetPlayerById:
    """Tests for get_player_by_id."""

    def test_returns_player_when_found(self, session, sample_player):
        """Test that existing player is returned."""
        result = get_player_by_id(session, sample_player.id)
        assert result is not None
        assert result.id == sample_player.id
        assert result.name == sample_player.name

    def test_returns_none_when_not_found(self, session):
        """Test that None is returned for non-existent player."""
        result = get_player_by_id(session, 99999)
        assert result is None


class TestGetPlayerByName:
    """Tests for get_player_by_name."""

    def test_returns_player_when_found(self, session, sample_player):
        """Test that existing player is returned by name."""
        result = get_player_by_name(session, sample_player.name)
        assert result is not None
        assert result.id == sample_player.id

    def test_returns_none_when_not_found(self, session):
        """Test that None is returned for non-existent name."""
        result = get_player_by_name(session, "Nonexistent Player")
        assert result is None


class TestGetPlayerByNickname:
    """Tests for get_player_by_nickname."""

    def test_returns_player_when_found(self, session, sample_player_with_nickname):
        """Test that player is returned when nickname exists."""
        result = get_player_by_nickname(session, "Johnny")
        assert result is not None
        assert result.id == sample_player_with_nickname.id
        assert result.name == "John Doe"

    def test_returns_none_when_not_found(self, session):
        """Test that None is returned for non-existent nickname."""
        result = get_player_by_nickname(session, "UnknownNick")
        assert result is None


class TestGetAllPlayers:
    """Tests for get_all_players."""

    def test_returns_empty_list_when_no_players(self, session):
        """Test that empty list is returned when no players exist."""
        result = get_all_players(session)
        assert result == []

    def test_returns_all_players(self, session):
        """Test that all players are returned."""
        player1 = Player(name="Player One")
        player2 = Player(name="Player Two")
        session.add_all([player1, player2])
        session.commit()

        result = get_all_players(session)
        assert len(result) == 2
        names = {p.name for p in result}
        assert names == {"Player One", "Player Two"}


class TestCreatePlayer:
    """Tests for create_player."""

    def test_flushes_and_populates_id(self, session):
        """Test that create_player flushes and populates ID."""
        player = Player(name="New Player")
        assert player.id is None

        result = create_player(session, player)

        assert result.id is not None
        assert result.name == "New Player"

    def test_duplicate_name_raises_integrity_error(self, session, sample_player):
        """Test that duplicate name raises IntegrityError."""
        duplicate = Player(name=sample_player.name)
        session.add(duplicate)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


class TestUpdatePlayer:
    """Tests for update_player."""

    def test_updates_existing_player(self, session, sample_player):
        """Test that player is updated."""
        sample_player.flag = "🇨🇦"
        sample_player.net = 500.0

        update_player(session, sample_player)
        session.commit()
        session.refresh(sample_player)

        assert sample_player.flag == "🇨🇦"
        assert sample_player.net == pytest.approx(500.0)


class TestCreateNickname:
    """Tests for create_nickname."""

    def test_creates_nickname(self, session, sample_player):
        """Test that nickname is created."""
        nickname = PlayerNickname(
            nickname="TestNick",
            player_name=sample_player.name,
            player_id=sample_player.id,
        )

        result = create_nickname(session, nickname)
        session.commit()

        assert result.nickname == "TestNick"
        assert result.player_id == sample_player.id

    def test_duplicate_nickname_raises_integrity_error(
        self, session, sample_player_with_nickname
    ):
        """Test that duplicate nickname raises IntegrityError."""
        duplicate = PlayerNickname(
            nickname="Johnny",  # Already exists
            player_name="Another Player",
            player_id=sample_player_with_nickname.id,
        )
        session.add(duplicate)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
