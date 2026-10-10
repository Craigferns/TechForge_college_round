"""FastAPI dependencies for database access and configuration."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends

from agentbreak.config import get_settings
from agentbreak.db import get_connection, migrate


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a managed SQLite connection with WAL mode and schema migration guaranteed."""
    settings = get_settings()
    conn = get_connection(settings.db_path)
    migrate(conn)
    try:
        yield conn
    finally:
        conn.close()


DbDep = Annotated[sqlite3.Connection, Depends(get_db)]
