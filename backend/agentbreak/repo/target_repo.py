"""Target agent repository."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.db import transaction
from agentbreak.schemas.target import Target


class TargetRepo:
    """Data access layer for evaluated agent targets."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, target: Target) -> Target:
        """Insert a new target configuration."""
        sql = """
        INSERT INTO target (id, name, kind, config_json, active_policy_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    target.id,
                    target.name,
                    target.kind,
                    json.dumps(target.config),
                    target.active_policy_id,
                    target.created_at,
                ),
            )
        return target

    def get(self, target_id: str) -> Target | None:
        """Fetch target by its ID."""
        sql = """
        SELECT id, name, kind, config_json, active_policy_id, created_at
        FROM target
        WHERE id = ?;
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, (target_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_model(row)

    def get_by_name(self, name: str) -> Target | None:
        """Fetch target by its unique name."""
        sql = """
        SELECT id, name, kind, config_json, active_policy_id, created_at
        FROM target
        WHERE name = ?;
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, (name,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_model(row)

    def list(self) -> list[Target]:
        """List all registered agent targets."""
        sql = """
        SELECT id, name, kind, config_json, active_policy_id, created_at
        FROM target
        ORDER BY created_at ASC;
        """
        cursor = self.conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [self._row_to_model(r) for r in rows]

    def delete(self, target_id: str) -> bool:
        """Delete target by ID."""
        sql = "DELETE FROM target WHERE id = ?;"
        with transaction(self.conn):
            cur = self.conn.execute(sql, (target_id,))
            return cur.rowcount > 0

    def update_active_policy(self, target_id: str, policy_id: str) -> bool:
        """Update active security policy ID for a target."""
        sql = "UPDATE target SET active_policy_id = ? WHERE id = ?;"
        with transaction(self.conn):
            cur = self.conn.execute(sql, (policy_id, target_id))
            return cur.rowcount > 0

    @staticmethod
    def _row_to_model(row: sqlite3.Row | Any) -> Target:
        return Target(
            id=row["id"],
            name=row["name"],
            kind=row["kind"],
            config=json.loads(row["config_json"]),
            active_policy_id=row["active_policy_id"],
            created_at=row["created_at"],
        )
