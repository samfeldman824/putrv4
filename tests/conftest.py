"""Pytest configuration and shared fixtures."""

from collections.abc import Generator
from pathlib import Path
import tempfile

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.models.models import Game, Player, PlayerGameStats, PlayerNickname


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(test_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def sample_player(session) -> Player:
    """Create a sample player for testing."""
    player = Player(name="Test Player", flag="🇺🇸", putr="5.0")
    session.add(player)
    session.commit()
    session.refresh(player)
    return player


@pytest.fixture
def sample_player_with_nickname(session) -> Player:
    """Create a sample player with a nickname."""
    player = Player(name="John Doe", flag="🇬🇧", putr="UR")
    session.add(player)
    session.flush()

    nickname = PlayerNickname(
        nickname="Johnny", player_name="John Doe", player_id=player.id
    )
    session.add(nickname)
    session.commit()
    session.refresh(player)
    return player


@pytest.fixture
def sample_game(session) -> Game:
    """Create a sample game for testing."""
    game = Game(date_str="23_10_07", ledger_filename="ledger23_10_07.csv")
    session.add(game)
    session.commit()
    session.refresh(game)
    return game


@pytest.fixture
def sample_games(session) -> list[Game]:
    """Create multiple games for testing chronological ordering."""
    games_data = [
        ("23_09_26", "ledger23_09_26.csv"),
        ("23_09_29", "ledger23_09_29.csv"),
        ("23_10_02", "ledger23_10_02.csv"),
        ("23_10_07", "ledger23_10_07.csv"),
        ("23_10_07(1)", "ledger23_10_07(1).csv"),
    ]
    games = []
    for date_str, filename in games_data:
        game = Game(date_str=date_str, ledger_filename=filename)
        session.add(game)
        games.append(game)
    session.commit()
    for game in games:
        session.refresh(game)
    return games


@pytest.fixture
def player_with_game_stats(session, sample_player, sample_games) -> Player:
    """Create a player with multiple game stats for testing calculations."""
    # Game results: +100, -50, +200, -75, +25 = total +200
    nets = [100.0, -50.0, 200.0, -75.0, 25.0]
    for game, net in zip(sample_games, nets, strict=True):
        stats = PlayerGameStats(
            player_id=sample_player.id,
            game_id=game.id,
            net=net,
        )
        session.add(stats)
    session.commit()
    session.refresh(sample_player)
    return sample_player


@pytest.fixture
def temp_csv_file() -> Generator[Path, None, None]:
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, prefix="ledger23_11_25"
    ) as f:
        f.write("player_nickname,player_id,buy_in,buy_out,stack,net\n")
        f.write("Test Player,abc123,100,200,200,100\n")
        f.write("John Doe,def456,150,50,50,-100\n")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()
