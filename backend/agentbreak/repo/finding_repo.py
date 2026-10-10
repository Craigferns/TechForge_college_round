"""Repository for persisting, updating, and querying vulnerability findings."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from agentbreak.db import transaction
from agentbreak.schemas.finding import Finding


def compute_finding_fingerprint(target_id: str, case_id: str) -> str:
    """Compute stable fingerprint uniquely identifying an attack case vulnerability on a target."""
    raw = f"{target_id}:{case_id}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"fnd_fp_{digest[:16]}"


class FindingRepo:
    """SQLite repository for finding and finding_run tables."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, finding_id: str) -> Finding | None:
        """Retrieve finding by ID."""
        sql = "SELECT * FROM finding WHERE id = ?;"
        cursor = self.conn.cursor()
        cursor.execute(sql, (finding_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_finding(row)

    def get_by_fingerprint(self, fingerprint: str) -> Finding | None:
        """Retrieve finding by fingerprint."""
        sql = "SELECT * FROM finding WHERE fingerprint = ?;"
        cursor = self.conn.cursor()
        cursor.execute(sql, (fingerprint,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_finding(row)

    def upsert_finding(
        self,
        target_id: str,
        scenario_id: str,
        case_id: str,
        title: str,
        severity: str,
        impact_class: str,
        run_id: str,
        timestamp: str,
        success_rate: float = 1.0,
        confidence: str = "confirmed",
        enabling_permissions: list[str] | None = None,
    ) -> Finding:
        """Upsert a finding for a successful exploit run.

        If a finding with this fingerprint exists, increments occurrences and updates last_run_id.
        Avoids duplicate findings and links runs in finding_run table.
        """
        fingerprint = compute_finding_fingerprint(target_id, case_id)
        existing = self.get_by_fingerprint(fingerprint)

        with transaction(self.conn):
            if existing is None:
                finding_id = f"fnd_{hashlib.sha256(fingerprint.encode()).hexdigest()[:12]}"
                perms = enabling_permissions or []
                sql_insert = """
                INSERT INTO finding (
                    id, fingerprint, target_id, scenario_id, case_id, title,
                    severity, impact_class, status, success_rate, confidence,
                    enabling_permissions_json, first_run_id, last_run_id,
                    occurrences, first_seen, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, 1, ?, ?);
                """
                self.conn.execute(
                    sql_insert,
                    (
                        finding_id,
                        fingerprint,
                        target_id,
                        scenario_id,
                        case_id,
                        title,
                        severity,
                        impact_class,
                        success_rate,
                        confidence,
                        json.dumps(perms),
                        run_id,
                        run_id,
                        timestamp,
                        timestamp,
                    ),
                )
                self.conn.execute(
                    "INSERT OR IGNORE INTO finding_run (finding_id, run_id) VALUES (?, ?);",
                    (finding_id, run_id),
                )
            else:
                finding_id = existing.id
                # Check if this run is already linked
                cur = self.conn.execute(
                    "SELECT 1 FROM finding_run WHERE finding_id = ? AND run_id = ?;",
                    (finding_id, run_id),
                )
                already_linked = cur.fetchone() is not None

                new_occurrences = existing.occurrences + (0 if already_linked else 1)
                sql_update = """
                UPDATE finding SET
                    occurrences = ?,
                    last_run_id = ?,
                    last_seen = ?,
                    success_rate = ?,
                    confidence = ?
                WHERE id = ?;
                """
                self.conn.execute(
                    sql_update,
                    (
                        new_occurrences,
                        run_id,
                        timestamp,
                        success_rate,
                        confidence,
                        finding_id,
                    ),
                )
                self.conn.execute(
                    "INSERT OR IGNORE INTO finding_run (finding_id, run_id) VALUES (?, ?);",
                    (finding_id, run_id),
                )

        updated = self.get(finding_id)
        assert updated is not None
        return updated

    def update_metrics(
        self,
        finding_id: str,
        success_rate: float,
        confidence: str,
    ) -> Finding | None:
        """Update trials success_rate and confidence for an existing finding."""
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE finding SET success_rate = ?, confidence = ? WHERE id = ?;",
                (success_rate, confidence, finding_id),
            )
        return self.get(finding_id)

    def update_status(self, finding_id: str, status_val: str) -> Finding | None:
        """Update status of a finding (e.g. open, accepted_risk)."""
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE finding SET status = ? WHERE id = ?;",
                (status_val, finding_id),
            )
        return self.get(finding_id)

    def list_findings(
        self,
        target_id: str | None = None,
        scenario_id: str | None = None,
        severity: str | None = None,
        status_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Finding]:
        """List findings matching optional filter criteria."""
        conditions: list[str] = []
        params: list[Any] = []

        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)
        if scenario_id:
            conditions.append("scenario_id = ?")
            params.append(scenario_id)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
        SELECT * FROM finding
        {where_clause}
        ORDER BY last_seen DESC, id ASC
        LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [self._row_to_finding(r) for r in rows]

    def count_findings(
        self,
        target_id: str | None = None,
        scenario_id: str | None = None,
        severity: str | None = None,
        status_filter: str | None = None,
    ) -> int:
        """Count findings matching optional filter criteria."""
        conditions: list[str] = []
        params: list[Any] = []

        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)
        if scenario_id:
            conditions.append("scenario_id = ?")
            params.append(scenario_id)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT COUNT(*) FROM finding {where_clause};"
        cursor = self.conn.cursor()
        cursor.execute(sql, tuple(params))
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    def get_runs_for_finding(self, finding_id: str) -> list[str]:
        """Fetch all run IDs associated with a finding."""
        sql = "SELECT run_id FROM finding_run WHERE finding_id = ? ORDER BY run_id ASC;"
        cursor = self.conn.cursor()
        cursor.execute(sql, (finding_id,))
        return [r["run_id"] for r in cursor.fetchall()]

    @staticmethod
    def _row_to_finding(row: sqlite3.Row | Any) -> Finding:
        perms = (
            json.loads(row["enabling_permissions_json"]) if row["enabling_permissions_json"] else []
        )
        return Finding(
            id=row["id"],
            fingerprint=row["fingerprint"],
            target_id=row["target_id"],
            scenario_id=row["scenario_id"],
            case_id=row["case_id"],
            title=row["title"],
            severity=row["severity"],
            impact_class=row["impact_class"],
            status=row["status"],
            success_rate=float(row["success_rate"]),
            confidence=row["confidence"],
            enabling_permissions=perms,
            first_run_id=row["first_run_id"],
            last_run_id=row["last_run_id"],
            occurrences=int(row["occurrences"]),
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
        )
