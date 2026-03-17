"""Shared database connection helper for ADK tools."""

import os
import re
import sqlite3
from pathlib import Path

_bundled = Path(__file__).resolve().parent / "mineralwatch.db"
_dev = Path(__file__).resolve().parent.parent.parent.parent / "data" / "mineralwatch.db"
DB_PATH = Path(os.environ.get(
    "MINERALWATCH_DB_PATH",
    str(_bundled if _bundled.exists() else _dev),
))

USGS_COL = 'USGS Commodity Name\n(exact CSV name)'

# Default score for unknown risk levels — used across tools for consistency.
DEFAULT_RISK_SCORE = 50


def get_db_conn() -> sqlite3.Connection:
    """Return a connection to the mineralwatch SQLite database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Set BACKEND_API_URL env var for cloud deployment."
        )
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def strip_mineral_qualifier(name: str) -> str:
    """Strip parenthetical qualifiers and trailing asterisks from mineral names.

    Matrix columns like 'HAFNIUM (see ZIRCONIUM)' or 'DIAMOND (INDUSTRIAL)*'
    need to be reduced to their base name for USGS lookups.
    """
    name = re.sub(r"\s*\(.*?\)", "", name)
    name = name.strip("* ").strip()
    return name
