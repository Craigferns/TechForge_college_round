"""Findings repository for persistence, deduplication, and upsert."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.schemas.finding import Finding


class FindingRepo:
    """Repository handling CRUD and fingerprint-based upsert for findings."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, finding_id: str) -> Finding | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, fingerprint, target_id, scenario_id, case_id, title, severity,
                   impact_class, status, success_rate, confidence, enabling_permissions_json,
                   first_run_id, last_run_id, occurrences, first_seen, last_seen
            FROM finding
            WHERE id = ?
            """,
            (finding_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_finding(row)

    def get_by_fingerprint(self, fingerprint: str) -> Finding | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, fingerprint, target_id, scenario_id, case_id, title, severity,
                   impact_class, status, success_rate, confidence, enabling_permissions_json,
                   first_run_id, last_run_id, occurrences, first_seen, last_seen
            FROM finding
            WHERE fingerprint = ?
            """,
            (fingerprint,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_finding(row)

    def list_findings(
        self,
        severity: str | None = None,
        status_filter: str | None = None,
        scenario_id: str | None = None,
        target_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Finding], int]:
        cursor = self.conn.cursor()
        conditions: list[str] = []
        params: list[Any] = []

        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)
        if scenario_id:
            conditions.append("scenario_id = ?")
            params.append(scenario_id)
        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(f"SELECT COUNT(*) FROM finding {where_clause}", params)
        total = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT id, fingerprint, target_id, scenario_id, case_id, title, severity,
                   impact_class, status, success_rate, confidence, enabling_permissions_json,
                   first_run_id, last_run_id, occurrences, first_seen, last_seen
            FROM finding
            {where_clause}
            ORDER BY first_seen DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        )
        rows = cursor.fetchall()
        return [self._row_to_finding(r) for r in rows], total

    def upsert_from_run(
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
        on_active_policy: bool = False,
    ) -> Finding:
        """Upsert finding keyed by fingerprint = sha256(target_id:case_id:impact_class).

        A fixed finding exploited again under the target's *active* policy becomes 'regressed';
        exploits under other (e.g. older baseline) policies only add evidence.
        """
        import hashlib
        import uuid

        fp_raw = f"{target_id}:{case_id}:{impact_class}"
        fingerprint = f"fp_{hashlib.sha256(fp_raw.encode('utf-8')).hexdigest()[:16]}"
        existing = self.get_by_fingerprint(fingerprint)
        perms: list[str] = enabling_permissions or []

        if existing:
            # Update existing finding
            new_occurrences = existing.occurrences + 1
            new_status = (
                "regressed" if existing.status == "fixed" and on_active_policy else existing.status
            )
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE finding
                SET occurrences = ?,
                    last_seen = ?,
                    last_run_id = ?,
                    success_rate = ?,
                    confidence = ?,
                    status = ?
                WHERE id = ?
                """,
                (
                    new_occurrences,
                    timestamp,
                    run_id,
                    success_rate,
                    confidence,
                    new_status,
                    existing.id,
                ),
            )
            # Link finding_run
            cursor.execute(
                "INSERT OR IGNORE INTO finding_run (finding_id, run_id) VALUES (?, ?)",
                (existing.id, run_id),
            )
            self.conn.commit()
            updated = self.get(existing.id)
            if updated is None:
                raise RuntimeError(f"Failed to reload finding '{existing.id}' after update.")
            return updated

        # Create new finding
        finding_id = f"fnd_{uuid.uuid4().hex[:12]}"
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO finding (
                id, fingerprint, target_id, scenario_id, case_id, title, severity,
                impact_class, status, success_rate, confidence, enabling_permissions_json,
                first_run_id, last_run_id, occurrences, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding_id,
                fingerprint,
                target_id,
                scenario_id,
                case_id,
                title,
                severity,
                impact_class,
                "open",
                success_rate,
                confidence,
                json.dumps(perms),
                run_id,
                run_id,
                1,
                timestamp,
                timestamp,
            ),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO finding_run (finding_id, run_id) VALUES (?, ?)",
            (finding_id, run_id),
        )
        self.conn.commit()
        created = self.get(finding_id)
        if created is None:
            raise RuntimeError(f"Failed to reload finding '{finding_id}' after insert.")
        return created

    def update_status(self, finding_id: str, status: str) -> Finding | None:
        cursor = self.conn.cursor()
        cursor.execute("UPDATE finding SET status = ? WHERE id = ?", (status, finding_id))
        self.conn.commit()
        return self.get(finding_id)

    def _row_to_finding(self, row: tuple[Any, ...]) -> Finding:
        return Finding(
            id=row[0],
            fingerprint=row[1],
            target_id=row[2],
            scenario_id=row[3],
            case_id=row[4],
            title=row[5],
            severity=row[6],
            impact_class=row[7],
            status=row[8],
            success_rate=row[9],
            confidence=row[10],
            enabling_permissions=json.loads(row[11]),
            first_run_id=row[12],
            last_run_id=row[13],
            occurrences=row[14],
            first_seen=row[15],
            last_seen=row[16],
        )
