"""Repository for PermissionAudit persistence."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.schemas.audit import AuditProof, PermissionAudit, PermissionRow


class AuditRepo:
    """Repository handling CRUD operations for permission audits."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, audit: PermissionAudit) -> PermissionAudit:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO permission_audit (
                id, target_id, policy_id, status, stage, granted_json,
                needed_json, excess_json, rows_json, minimal_policy_id, proof_json,
                created_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
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
        self.conn.commit()
        return audit

    def get(self, audit_id: str) -> PermissionAudit | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, target_id, policy_id, status, stage, granted_json,
                   needed_json, excess_json, rows_json, minimal_policy_id, proof_json,
                   created_at, finished_at
            FROM permission_audit
            WHERE id = ?
            """,
            (audit_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        rows_data = json.loads(row[8] or "[]")
        proof_data = json.loads(row[10]) if row[10] else None

        return PermissionAudit(
            id=row[0],
            target_id=row[1],
            policy_id=row[2],
            status=row[3],
            stage=row[4],
            granted=json.loads(row[5] or "[]"),
            needed=json.loads(row[6] or "[]"),
            excess=json.loads(row[7] or "[]"),
            rows=[PermissionRow.model_validate(r) for r in rows_data],
            minimal_policy_id=row[9],
            proof=AuditProof.model_validate(proof_data) if proof_data else None,
            created_at=row[11],
            finished_at=row[12],
        )

    def list(
        self, target_id: str | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[PermissionAudit], int]:
        cursor = self.conn.cursor()
        conds = []
        params: list[Any] = []
        if target_id:
            conds.append("target_id = ?")
            params.append(target_id)
        where = f"WHERE {' AND '.join(conds)}" if conds else ""

        cursor.execute(f"SELECT COUNT(*) FROM permission_audit {where}", params)
        total = cursor.fetchone()[0]

        cursor.execute(
            f"SELECT id FROM permission_audit {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        rows = cursor.fetchall()
        items: list[PermissionAudit] = []
        for r in rows:
            a = self.get(r[0])
            if a:
                items.append(a)
        return items, total

    def update(self, audit: PermissionAudit) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE permission_audit
            SET status = ?,
                stage = ?,
                granted_json = ?,
                needed_json = ?,
                excess_json = ?,
                rows_json = ?,
                minimal_policy_id = ?,
                proof_json = ?,
                finished_at = ?
            WHERE id = ?
            """,
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
        self.conn.commit()
