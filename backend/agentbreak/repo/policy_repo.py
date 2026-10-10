"""Policy repository."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.db import transaction
from agentbreak.schemas.policy import Grant, Policy


class PolicyRepo:
    """Data access layer for immutable security policies."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, policy: Policy) -> Policy:
        """Insert a new policy."""
        sql = """
        INSERT INTO policy (id, name, parent_id, grants_json, hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        grants_data = [g.model_dump() for g in policy.grants]
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    policy.id,
                    policy.name,
                    policy.parent_id,
                    json.dumps(grants_data),
                    policy.hash,
                    policy.created_at,
                ),
            )
        return policy

    def get(self, policy_id: str) -> Policy | None:
        """Fetch policy by ID."""
        sql = """
        SELECT id, name, parent_id, grants_json, hash, created_at
        FROM policy
        WHERE id = ?;
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, (policy_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_model(row)

    def get_by_hash(self, policy_hash: str) -> Policy | None:
        """Fetch policy by canonical SHA-256 hash."""
        sql = """
        SELECT id, name, parent_id, grants_json, hash, created_at
        FROM policy
        WHERE hash = ?;
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, (policy_hash,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_model(row)

    def list(self) -> list[Policy]:
        """List all registered security policies."""
        sql = """
        SELECT id, name, parent_id, grants_json, hash, created_at
        FROM policy
        ORDER BY created_at ASC;
        """
        cursor = self.conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row: sqlite3.Row | Any) -> Policy:
        raw_grants = json.loads(row["grants_json"])
        grants = [Grant.model_validate(g) for g in raw_grants]
        return Policy(
            id=row["id"],
            name=row["name"],
            parent_id=row["parent_id"],
            grants=grants,
            hash=row["hash"],
            created_at=row["created_at"],
        )
