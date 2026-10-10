"""Database layer: SQLite connection management, transactions, migrations, and ID generator."""

from __future__ import annotations

import contextlib
import secrets
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from agentbreak.config import get_settings


def new_id(prefix: str) -> str:
    """Generate a clean, reproducible prefixed identifier like 'run_1a2b3c4d'."""
    suffix = secrets.token_hex(4)
    return f"{prefix}_{suffix}"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open and configure an SQLite database connection.

    Applies WAL journal mode, enables foreign keys, and configures a 5000ms busy timeout
    to prevent locks on Windows multi-threaded access.
    """
    if db_path is None:
        db_path = get_settings().db_path

    # Ensure parent directory exists for file-backed databases
    if isinstance(db_path, Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    elif isinstance(db_path, str) and db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Enforce SQLite performance and integrity pragmas
    conn.execute("PRAGMA foreign_keys = ON;")
    if str(db_path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")

    return conn


@contextlib.contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Context manager for atomic SQLite transactions with automatic commit/rollback."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def migrate(conn: sqlite3.Connection) -> int:
    """Apply schema migrations idempotently using PRAGMA user_version.

    Returns the resulting schema version (1 for current schema).
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version;")
    row = cursor.fetchone()
    current_version = row[0] if row else 0

    if current_version == 0:
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, encoding="utf-8") as f:
            ddl_script = f.read()

        with transaction(conn):
            conn.executescript(ddl_script)
            conn.execute("PRAGMA user_version = 1;")
        return 1

    return current_version
