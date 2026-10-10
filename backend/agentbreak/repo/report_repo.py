"""Repository for persistent markdown evidence reports."""

from __future__ import annotations

import json
import sqlite3

from agentbreak.schemas.dashboard import Report


class ReportRepo:
    """Repository handling CRUD operations for evidence reports."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, report: Report) -> Report:
        cursor = self.conn.cursor()
        scope = {"target_id": report.target_id, "policy_id": report.policy_id}
        cursor.execute(
            """
            INSERT INTO report (id, scope_json, format, markdown, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report.id,
                json.dumps(scope),
                "markdown",
                report.markdown,
                json.dumps(report.meta),
                report.created_at,
            ),
        )
        self.conn.commit()
        return report

    def get(self, report_id: str) -> Report | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, scope_json, markdown, meta_json, created_at
            FROM report
            WHERE id = ?
            """,
            (report_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        scope = json.loads(row[1] or "{}")
        return Report(
            id=row[0],
            target_id=scope.get("target_id", ""),
            policy_id=scope.get("policy_id", ""),
            markdown=row[2],
            meta=json.loads(row[3] or "{}"),
            created_at=row[4],
        )

    def list(self, limit: int = 50, offset: int = 0) -> tuple[list[Report], int]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM report")
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT id FROM report ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
        )
        rows = cursor.fetchall()
        items: list[Report] = []
        for r in rows:
            rep = self.get(r[0])
            if rep:
                items.append(rep)
        return items, total
