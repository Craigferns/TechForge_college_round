"""Repository for permission audit data persistence."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.db import transaction
from agentbreak.schemas.audit import AuditProof, PermissionAudit, PermissionRow


class AuditRepo:
    """SQLite data access for permission audits."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, audit: PermissionAudit) -> PermissionAudit:
        """Insert a new permission audit record."""
        sql = """
        INSERT INTO permission_audit (
            id, target_id, policy_id, status, stage,
            granted_json, needed_json, excess_json, rows_json,
            minimal_policy_id, proof_json, created_at, finished_at
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?
        );
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    audit.id,
                    audit.target_id,
                    audit.policy_id,
                    audit.status,
                    audit.stage,
                    json.dumps(audit.granted),
                    json.dumps(audit.needed),
                    json.dumps(audit.excess),
                    json.dumps([r.model_dump() for r in audit.rows]),
                    audit.minimal_policy_id,
                    json.dumps(audit.proof.model_dump()) if audit.proof else None,
                    audit.created_at,
                    audit.finished_at,
                ),
            )
        return audit

    def update(self, audit: PermissionAudit) -> PermissionAudit:
        """Update an existing permission audit record."""
        sql = """
        UPDATE permission_audit
        SET status = ?, stage = ?, granted_json = ?, needed_json = ?, excess_json = ?,
            rows_json = ?, minimal_policy_id = ?, proof_json = ?, finished_at = ?
        WHERE id = ?;
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    audit.status,
                    audit.stage,
                    json.dumps(audit.granted),
                    json.dumps(audit.needed),
                    json.dumps(audit.excess),
                    json.dumps([r.model_dump() for r in audit.rows]),
                    audit.minimal_policy_id,
                    json.dumps(audit.proof.model_dump()) if audit.proof else None,
                    audit.finished_at,
                    audit.id,
                ),
            )
        return audit

    def get(self, audit_id: str) -> PermissionAudit | None:
        """Retrieve permission audit by ID."""
        sql = """
        SELECT id, target_id, policy_id, status, stage,
               granted_json, needed_json, excess_json, rows_json,
               minimal_policy_id, proof_json, created_at, finished_at
        FROM permission_audit
        WHERE id = ?;
        """
        row = self.conn.execute(sql, (audit_id,)).fetchone()
        if not row:
            return None
        return self._row_to_audit(row)

    def list_audits(
        self,
        target_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PermissionAudit]:
        """List permission audits with optional target filtering."""
        conditions: list[str] = []
        params: list[object] = []

        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
        SELECT id, target_id, policy_id, status, stage,
               granted_json, needed_json, excess_json, rows_json,
               minimal_policy_id, proof_json, created_at, finished_at
        FROM permission_audit
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_audit(r) for r in rows]

    def count_audits(self, target_id: str | None = None) -> int:
        """Count total permission audits."""
        conditions: list[str] = []
        params: list[object] = []

        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT COUNT(*) FROM permission_audit {where_clause};"
        return int(self.conn.execute(sql, params).fetchone()[0])

    def _row_to_audit(self, row: sqlite3.Row | tuple[Any, ...]) -> PermissionAudit:
        rows_data = json.loads(row[8]) if row[8] else []
        proof_data = json.loads(row[10]) if row[10] else None

        return PermissionAudit(
            id=row[0],
            target_id=row[1],
            policy_id=row[2],
            status=row[3],
            stage=row[4],
            granted=json.loads(row[5]) if row[5] else [],
            needed=json.loads(row[6]) if row[6] else [],
            excess=json.loads(row[7]) if row[7] else [],
            rows=[PermissionRow.model_validate(r) for r in rows_data],
            minimal_policy_id=row[9],
            proof=AuditProof.model_validate(proof_data) if proof_data else None,
            created_at=row[11],
            finished_at=row[12],
        )
