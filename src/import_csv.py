"""Script to import CSV ledger files into PostgreSQL database."""

from src.services.import_service import (
    add_records,
    import_all_ledgers_strict,
    reset_db,
)

if __name__ == "__main__":
    reset_db()
    add_records()
    import_all_ledgers_strict()
