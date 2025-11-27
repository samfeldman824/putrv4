import csv
from enum import Enum
import json
from pathlib import Path
from typing import TypedDict, cast

from loguru import logger
from sqlmodel import Session, SQLModel, select

from src.core.db import create_db_and_tables, engine
from src.models import Game, LedgerEntry, Player, PlayerGameStats, PlayerNickname
from src.services.player_stats_service import recalculate_player_stats


class ImportResult(Enum):
    """Result of importing a single ledger file."""

    SUCCESS = "success"
    GAME_EXISTS = "game_exists"
    MISSING_NICKNAMES = "missing_nicknames"


class PlayerBackupData(TypedDict):
    """Structure of player data in backup JSON file."""

    flag: str
    putr: str
    player_nicknames: list[str]


def add_records(backup_file: str = "full_backup.json") -> None:
    """Add records from a backup file. Skips players that already exist."""

    with Path(backup_file).open("r", encoding="utf-8") as f:
        backup_data = cast("dict[str, PlayerBackupData]", json.load(f))

    added_count = 0
    skipped_count = 0

    with Session(engine) as session:
        for player_name, player_data in backup_data.items():
            # Check if player already exists
            existing_player = session.exec(
                select(Player).where(Player.name == player_name)
            ).first()
            if existing_player:
                skipped_count += 1
                continue

            player = Player(
                name=player_name, flag=player_data["flag"], putr=player_data["putr"]
            )
            session.add(player)
            session.flush()  # Populates player.id
            if player.id is None:
                msg = "Player ID should be populated after flush"
                raise ValueError(msg)
            for nickname in player_data["player_nicknames"]:
                session.add(
                    PlayerNickname(
                        nickname=nickname, player_name=player_name, player_id=player.id
                    )
                )
            session.commit()
            added_count += 1
    logger.success(f"Added {added_count} players, skipped {skipped_count} existing.")


def reset_db() -> None:
    """Drop and recreate all tables, then populate nicknames."""
    logger.warning("Resetting database...")
    SQLModel.metadata.drop_all(engine)
    logger.info("Recreating tables...")
    create_db_and_tables()

    logger.success("Database reset successfully.")


def import_all_ledgers(ledgers_dir: str = "ledgers") -> None:
    """Import all CSV files from the ledgers directory strictly (no new players)."""
    ledgers_path = Path(ledgers_dir)

    if not ledgers_path.exists():
        logger.error(f"Error: {ledgers_dir} directory not found")
        return

    csv_files = sorted(ledgers_path.glob("*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files to import (STRICT MODE)")

    with Session(engine) as session:
        for csv_file in csv_files:
            logger.info(f"Processing (Strict): {csv_file.name}")
            import_single_ledger(session, csv_file)
        session.commit()
        logger.success("All files imported successfully (Strict Mode)!")


def _parse_float(val: str | None) -> float:
    """Parse a float value safely, returning 0.0 for empty/None values."""
    if not val or not val.strip():
        return 0.0
    return float(val)


def _validate_ledger_nicknames(
    session: Session, csv_file: Path
) -> tuple[list[dict[str, str]], list[Player]] | None:
    """Validate all nicknames in a ledger file exist.

    Returns (rows, players) if all valid, None if any nickname is missing.
    """
    rows: list[dict[str, str]] = []
    players: list[Player] = []
    missing_nicknames: list[str] = []

    with csv_file.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            player = find_player_by_nickname(session, row)
            if player:
                players.append(player)
            else:
                nickname = row.get("player_nickname", "<unknown>")
                missing_nicknames.append(nickname)

    if missing_nicknames:
        logger.error(
            f"Abandoning ledger {csv_file.name}: missing nicknames: {missing_nicknames}"
        )
        return None

    return rows, players


def import_single_ledger(session: Session, csv_file: Path) -> ImportResult:
    """Import a single CSV ledger file strictly.

    Returns:
        ImportResult indicating the outcome of the import.
    """
    # Extract date from filename (e.g., "ledger23_09_26.csv" -> "23_09_26")
    date_str = csv_file.stem.replace("ledger", "")

    # First pass: validate all nicknames exist
    validation_result = _validate_ledger_nicknames(session, csv_file)
    if validation_result is None:
        return ImportResult.MISSING_NICKNAMES
    rows, players = validation_result

    # Check if game already exists
    if session.exec(select(Game).where(Game.date_str == date_str)).first():
        logger.info(f"Game {date_str} already exists, skipping...")
        return ImportResult.GAME_EXISTS

    game = Game(date_str=date_str, ledger_filename=csv_file.name)
    session.add(game)
    session.flush()  # Get the game ID

    if game.id is None:
        msg = "Game ID should be populated after flush"
        raise ValueError(msg)
    game_id: int = game.id

    # Check if ledger entries already exist for this game
    if session.exec(select(LedgerEntry).where(LedgerEntry.game_id == game_id)).first():
        logger.info(f"Game {date_str} already has ledger entries, skipping...")
        return ImportResult.GAME_EXISTS

    player_count = 0
    affected_player_ids: set[int] = set()

    # Second pass: process all rows (all nicknames are validated)
    for row, player in zip(rows, players, strict=True):
        # Player ID must exist since player was fetched from DB
        if player.id is None:
            msg = "Player ID should be populated for fetched player"
            raise ValueError(msg)
        player_id: int = player.id
        net = _parse_float(row.get("net"))

        existing_stats = session.exec(
            select(PlayerGameStats).where(
                PlayerGameStats.player_id == player_id,
                PlayerGameStats.game_id == game_id,
            )
        ).first()

        if not existing_stats:
            stats = PlayerGameStats(
                player_id=player_id,
                game_id=game_id,
                net=net,
            )
            session.add(stats)
            affected_player_ids.add(player_id)

        ledger_entry = LedgerEntry(
            game_id=game_id,
            player_id=player_id,
            player_nickname=row.get("player_nickname", ""),
            player_id_csv=row.get("player_id", ""),
            session_start_at=row.get("session_start_at"),
            session_end_at=row.get("session_end_at"),
            buy_in=_parse_float(row.get("buy_in")),
            buy_out=_parse_float(row.get("buy_out")),
            stack=_parse_float(row.get("stack")),
            net=net,
        )
        session.add(ledger_entry)
        player_count += 1

    # Recalculate stats for all affected players after importing the game
    for player_id in affected_player_ids:
        recalculate_player_stats(session, player_id)

    logger.info(
        f"Imported game {date_str}: {player_count} records, "
        + f"{len(affected_player_ids)} player stats updated"
    )

    return ImportResult.SUCCESS


def find_player_by_nickname(session: Session, row: dict[str, str]) -> Player | None:
    """Find a player based on CSV row data. Returns None if not found."""
    player_nickname = row.get("player_nickname")

    player = None

    # Try to find by Nickname
    nickname_obj = session.exec(
        select(PlayerNickname).where(PlayerNickname.nickname == player_nickname)
    ).first()
    if nickname_obj:
        player = nickname_obj.player

    return player
