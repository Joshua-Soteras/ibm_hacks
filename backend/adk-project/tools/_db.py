"""Shared database connection helper for ADK tools."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "mineralwatch.db"


def get_db_conn() -> sqlite3.Connection:
    """Return a connection to the mineralwatch SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn
