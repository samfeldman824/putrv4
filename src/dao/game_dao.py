"""Data Access Object for Game operations."""

from sqlmodel import Session, select

from src.models.models import Game, LedgerEntry, PlayerGameStats


def get_game_by_id(session: Session, game_id: int) -> Game | None:
    """Get a game by ID."""
    return session.get(Game, game_id)


def get_game_by_date(session: Session, date_str: str) -> Game | None:
    """Get a game by date string."""
    return session.exec(select(Game).where(Game.date_str == date_str)).first()


def create_game(session: Session, game: Game) -> Game:
    """Create a new game and return it with ID populated."""
    session.add(game)
    session.flush()
    return game


def has_ledger_entries(session: Session, game_id: int) -> bool:
    """Check if a game has any ledger entries."""
    return (
        session.exec(select(LedgerEntry).where(LedgerEntry.game_id == game_id)).first()
        is not None
    )


def create_ledger_entry(session: Session, entry: LedgerEntry) -> LedgerEntry:
    """Create a new ledger entry."""
    session.add(entry)
    return entry


def get_player_game_stats(
    session: Session, player_id: int, game_id: int
) -> PlayerGameStats | None:
    """Get player stats for a specific game."""
    return session.exec(
        select(PlayerGameStats).where(
            PlayerGameStats.player_id == player_id,
            PlayerGameStats.game_id == game_id,
        )
    ).first()


def create_player_game_stats(
    session: Session, stats: PlayerGameStats
) -> PlayerGameStats:
    """Create new player game stats."""
    session.add(stats)
    return stats


def get_player_stats_with_games(
    session: Session, player_id: int
) -> list[tuple[PlayerGameStats, Game]]:
    """Get all game stats for a player with their associated games."""
    results = session.exec(
        select(PlayerGameStats, Game)
        .join(Game, PlayerGameStats.game_id == Game.id)  # type: ignore[arg-type]
        .where(PlayerGameStats.player_id == player_id)
    ).all()
    return list(results)
