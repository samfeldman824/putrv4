"""Service for calculating player aggregate statistics."""

from datetime import datetime

from loguru import logger
from sqlmodel import Session

from src.core.exceptions import ValidationError
from src.dao.game_dao import get_player_stats_with_games
from src.dao.player_dao import get_all_players, get_player_by_id, update_player

# Expected number of parts in date string: YY_MM_DD
DATE_PARTS_COUNT = 3


def parse_date_str(date_str: str) -> datetime:
    """Parse date_str format 'YY_MM_DD' or 'YY_MM_DD(N)' to datetime.

    Args:
        date_str: Date string in format 'YY_MM_DD' or 'YY_MM_DD(N)'
                  e.g., '23_09_26' or '23_09_26(2)'

    Returns:
        datetime object for sorting purposes
    """
    # Handle multiple games on same day: "23_09_26(2)" -> "23_09_26"
    base_date = date_str.split("(", maxsplit=1)[0]

    # Extract the game number suffix if present (for ordering same-day games)
    game_number = 0
    if "(" in date_str:
        try:
            game_number = int(date_str.split("(")[1].rstrip(")"))
        except (ValueError, IndexError):
            game_number = 0

    # Parse the base date
    parts = base_date.split("_")
    if len(parts) != DATE_PARTS_COUNT:
        raise ValidationError(
            message=f"Invalid date_str format: {date_str}",
            details={"date_str": date_str, "expected_format": "YY_MM_DD"},
        )

    year = int(parts[0]) + 2000  # '23' -> 2023
    month = int(parts[1])
    day = int(parts[2])

    # Use hour to differentiate same-day games
    return datetime(year, month, day, hour=game_number)


def recalculate_player_stats(session: Session, player_id: int) -> None:
    """Recalculate all aggregate stats for a player based on their game history.

    This calculates:
    - net: Total cumulative net
    - games_up: Number of games with positive net
    - games_down: Number of games with negative net
    - average_net: Average net per game
    - biggest_win: Largest single-game positive net
    - biggest_loss: Largest single-game negative net (stored as negative)
    - highest_net: Highest cumulative net ever reached (rolling max)
    - lowest_net: Lowest cumulative net ever reached (rolling min)

    Note: PUTR is manually entered and not calculated here.

    Args:
        session: Database session
        player_id: ID of the player to recalculate stats for
    """
    player = get_player_by_id(session, player_id)
    if not player:
        logger.warning(f"Player {player_id} not found, skipping stats calculation")
        return

    stats_with_games = get_player_stats_with_games(session, player_id)

    if not stats_with_games:
        # No games, reset stats to zero
        player.net = 0.0
        player.games_up = 0
        player.games_down = 0
        player.average_net = 0.0
        player.biggest_win = 0.0
        player.biggest_loss = 0.0
        player.highest_net = 0.0
        player.lowest_net = 0.0
        update_player(session, player)
        return

    # Sort by date (convert date_str to datetime for proper ordering)
    sorted_stats = sorted(
        stats_with_games,
        key=lambda x: parse_date_str(x[1].date_str),
    )

    # Calculate stats
    total_net = 0.0
    games_up = 0
    games_down = 0
    biggest_win = 0.0
    biggest_loss = 0.0
    highest_net = 0.0
    lowest_net = 0.0
    cumulative_net = 0.0

    for stat, _game in sorted_stats:
        game_net = stat.net

        # Update cumulative for rolling high/low
        cumulative_net += game_net

        # Track highest and lowest cumulative net
        highest_net = max(highest_net, cumulative_net)
        lowest_net = min(lowest_net, cumulative_net)

        # Count wins/losses
        if game_net > 0:
            games_up += 1
            biggest_win = max(biggest_win, game_net)
        elif game_net < 0:
            games_down += 1
            biggest_loss = min(biggest_loss, game_net)

        total_net += game_net

    # Calculate average
    total_games = len(sorted_stats)
    average_net = total_net / total_games if total_games > 0 else 0.0

    # Update player record
    player.net = total_net
    player.games_up = games_up
    player.games_down = games_down
    player.average_net = average_net
    player.biggest_win = biggest_win
    player.biggest_loss = biggest_loss
    player.highest_net = highest_net
    player.lowest_net = lowest_net

    update_player(session, player)
    logger.debug(
        f"Updated stats for {player.name}: "
        + f"net={total_net:.2f}, games={total_games}, avg={average_net:.2f}"
    )


def recalculate_all_player_stats(session: Session) -> None:
    """Recalculate stats for all players in the database.

    Useful for batch operations or data repair.
    """
    # Paginate through all players to handle large datasets
    offset = 0
    limit = 100
    total_processed = 0

    while True:
        players = get_all_players(session, offset=offset, limit=limit)
        if not players:
            break

        logger.info(f"Processing batch of {len(players)} players (offset={offset})...")

        for player in players:
            if player.id is not None:
                recalculate_player_stats(session, player.id)
                total_processed += 1

        # Break if we got fewer players than the limit (last page)
        if len(players) < limit:
            break

        offset += limit

    logger.success(f"Recalculated stats for {total_processed} players")
