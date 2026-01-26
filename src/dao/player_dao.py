"""Data Access Object for Player operations."""

from sqlmodel import Session, select

from src.models.models import Player, PlayerNickname


def get_player_by_id(session: Session, player_id: int) -> Player | None:
    """Get a player by ID."""
    return session.get(Player, player_id)


def get_player_by_name(session: Session, name: str) -> Player | None:
    """Get a player by name."""
    return session.exec(select(Player).where(Player.name == name)).first()


def get_all_players(
    session: Session, offset: int = 0, limit: int = 100
) -> list[Player]:
    """Get all players with pagination."""
    statement = select(Player).offset(offset).limit(limit)
    return list(session.exec(statement).all())


def create_player(session: Session, player: Player) -> Player:
    """Create a new player and return it with ID populated."""
    session.add(player)
    session.flush()
    return player


def update_player(session: Session, player: Player) -> Player:
    """Update an existing player."""
    session.add(player)
    return player


def get_player_by_nickname(session: Session, nickname: str) -> Player | None:
    """Find a player by their nickname."""
    nickname_obj = session.exec(
        select(PlayerNickname).where(PlayerNickname.nickname == nickname)
    ).first()
    if nickname_obj:
        return nickname_obj.player
    return None


def create_nickname(session: Session, nickname: PlayerNickname) -> PlayerNickname:
    """Create a new player nickname."""
    session.add(nickname)
    return nickname
