"""
Shared utilities for MCP tools

Provides database path resolution and thread-isolated SQLite connections
configured with `sqlite3.Row` dictionaries for all analytical sub-modules.
"""

import sqlite3
import os

_DEFAULT_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "capstone.db"))
DB_PATH = os.getenv("DATABASE_URL", _DEFAULT_DB)
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", DB_PATH))

def get_db_connection() -> sqlite3.Connection:
    """Return an isolated SQLite connection with row dictionary mapping."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

