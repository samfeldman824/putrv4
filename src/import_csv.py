"""Script to import CSV ledger files into PostgreSQL database."""

import csv
import json
from pathlib import Path
from typing import cast

from loguru import logger
from sqlmodel import Session, SQLModel, create_engine, select

from src.main import POSTGRES_URL, create_db_and_tables
from src.models import Game, LedgerEntry, Player, PlayerGameStats, PlayerNickname

# Create engine and tables
engine = create_engine(POSTGRES_URL)

def add_records(backup_file: str = "full_backup.json") -> None:
    """Add records from a backup file."""
    with open(backup_file, "r", encoding="utf-8") as f:
        backup_data = cast("dict[str, list[str]]", json.load(f))

    with Session(engine) as session:
        for player_name, player_data in backup_data.items():
            player = Player(name=player_name, flag=player_data["flag"], putr=player_data["putr"])
            session.add(player)
            session.flush()  # Populates player.id
            for nickname in player_data["player_nicknames"]:
                session.add(PlayerNickname(nickname=nickname, player_name=player_name, player_id=player.id))
            session.commit()
    logger.success(f"Populated {len(backup_data)} players.")

def reset_db() -> None:
    """Drop and recreate all tables, then populate nicknames."""
    logger.warning("Resetting database...")
    SQLModel.metadata.drop_all(engine)
    logger.info("Recreating tables...")
    create_db_and_tables()


    logger.success("Database reset successfully.")

def import_all_ledgers_strict(ledgers_dir: str = "ledgers") -> None:
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
            import_single_ledger_strict(session, csv_file)
        session.commit()
        logger.success("All files imported successfully (Strict Mode)!")


def import_single_ledger_strict(session: Session, csv_file: Path) -> None:
    """Import a single CSV ledger file strictly."""
    # Extract date from filename (e.g., "ledger23_09_26.csv" -> "23_09_26")
    date_str = csv_file.stem.replace("ledger", "")

    # Create game
    game = Game(date_str=date_str, ledger_filename=csv_file.name)
    session.add(game)
    session.flush()  # Get the game ID

    # Check if ledger entries already exist for this game
    if session.exec(select(LedgerEntry).where(LedgerEntry.game_id == game.id)).first():
        logger.info(f"Game {date_str} already has ledger entries, skipping...")
        return

    player_count = 0
    skipped_count = 0
    with csv_file.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            player = get_player_strict(session, row)
            
            # If player not found, SKIP
            if not player or not player.id or not game.id:
                skipped_count += 1
                continue

            # Helper to parse float safely
            def parse_float(val: str | None) -> float:
                if not val or not val.strip():
                    return 0.0
                return float(val)

            # Create PlayerGameStats record if not exists
            net = parse_float(row.get("net"))

            existing_stats = session.exec(
                select(PlayerGameStats).where(
                    PlayerGameStats.player_id == player.id,
                    PlayerGameStats.game_id == game.id,
                )
            ).first()

            if not existing_stats:
                stats = PlayerGameStats(
                    player_id=player.id,
                    game_id=game.id,
                    net=net,
                )
                session.add(stats)

            # Create LedgerEntry record (raw CSV data)
            ledger_entry = LedgerEntry(
                game_id=game.id,
                player_id=player.id,
                player_nickname=row.get("player_nickname", ""),
                player_id_csv=row.get("player_id", ""),
                session_start_at=row.get("session_start_at"),
                session_end_at=row.get("session_end_at"),
                buy_in=parse_float(row.get("buy_in")),
                buy_out=parse_float(row.get("buy_out")),
                stack=parse_float(row.get("stack")),
                net=net,
            )
            session.add(ledger_entry)

            player_count += 1

    logger.info(f"Imported game {date_str}: {player_count} records, {skipped_count} skipped")


def get_player_strict(session: Session, row: dict[str, str]) -> Player | None:
    """Find a player based on CSV row data. Returns None if not found."""
    player_id_str = row.get("player_id")
    player_nickname = row.get("player_nickname")

    player = None

    # 1. Try to find by unique player_id string from CSV
    if player_id_str:
        player = session.exec(
            select(Player).where(Player.player_id_str == player_id_str)
        ).first()

    # 2. Try to find by Nickname
    if not player and player_nickname:
        nickname_obj = session.exec(
            select(PlayerNickname).where(PlayerNickname.nickname == player_nickname)
        ).first()
        if nickname_obj:
            player = nickname_obj.player

    # 3. Fallback: try to find by canonical Name
    if not player and player_nickname:
        player = session.exec(
            select(Player).where(Player.name == player_nickname)
        ).first()

    # STRICT MODE: Do NOT create new player if not found
    
    # Update player_id_str if we found the player but they didn't have one
    if player and player_id_str and not player.player_id_str:
        player.player_id_str = player_id_str
        session.add(player)
        session.flush()

    return player


if __name__ == "__main__":
    # import sys

    # if "--reset" in sys.argv:
    #     reset_db()

    # import_ledger_files()

    reset_db()
    # create_db_and_tables()
    add_records()
    import_all_ledgers_strict()
