"""SQLModel data models for PUTR v4 application."""

from sqlmodel import Field, Relationship, SQLModel  # type: ignore


class Game(SQLModel, table=True):
    """Represents a single poker session/game."""

    id: int | None = Field(default=None, primary_key=True)
    date_str: str = Field(index=True, description="Format: YY_MM_DD or YY_MM_DD(N)")

    # We can link this to specific ledger CSV files later if needed
    ledger_filename: str | None = None

    # Relationships
    player_games: list["PlayerGameStats"] = Relationship(back_populates="game")  # type: ignore
    ledger_entries: list["LedgerEntry"] = Relationship(back_populates="game")  # type: ignore


class PlayerNickname(SQLModel, table=True):
    """Stores alternative names/nicknames for players for CSV matching."""

    id: int | None = Field(default=None, primary_key=True)
    nickname: str = Field(index=True, unique=True)
    player_name: str = Field(default="")
    player_id: int = Field(foreign_key="player.id")

    player: "Player" = Relationship(back_populates="nicknames")  # type: ignore


class Player(SQLModel, table=True):
    """Represents a player in the system."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    player_id_str: str | None = Field(
        default=None, description="The random string ID like '-6-yYmPWx-'"
    )
    flag: str = Field(default="")

    # Aggregate stats (can be re-calculated, but stored for quick access)
    putr: str = Field(
        default="0.0", description="Can be a float value or a string code like 'UR'"
    )
    net: float = 0.0
    biggest_win: float = 0.0
    biggest_loss: float = 0.0
    highest_net: float = 0.0
    lowest_net: float = 0.0

    games_up: int = 0
    games_down: int = 0
    average_net: float = 0.0

    # Relationships
    game_stats: list["PlayerGameStats"] = Relationship(back_populates="player")  # type: ignore
    ledger_entries: list["LedgerEntry"] = Relationship(back_populates="player")  # type: ignore

    # Nicknames stored in a separate table
    nicknames: list["PlayerNickname"] = Relationship(back_populates="player")  # type: ignore


class PlayerGameStats(SQLModel, table=True):
    """Link table between Player and Game with the result of that specific game."""

    id: int | None = Field(default=None, primary_key=True)

    player_id: int = Field(foreign_key="player.id")
    game_id: int = Field(foreign_key="game.id")

    net: float

    player: Player = Relationship(back_populates="game_stats")  # type: ignore
    game: Game = Relationship(back_populates="player_games")  # type: ignore


class LedgerEntry(SQLModel, table=True):
    """Represents a raw row from the ledger CSV file."""

    id: int | None = Field(default=None, primary_key=True)

    # Foreign Keys
    game_id: int = Field(foreign_key="game.id")
    player_id: int = Field(foreign_key="player.id")

    # Raw CSV Columns
    player_nickname: str
    player_id_csv: str = Field(description="The player_id column from CSV")
    session_start_at: str | None = None
    session_end_at: str | None = None
    buy_in: float = 0.0
    buy_out: float = 0.0
    stack: float = 0.0
    net: float = 0.0

    # Relationships
    game: Game = Relationship(back_populates="ledger_entries")  # type: ignore
    player: Player = Relationship(back_populates="ledger_entries")  # type: ignore
