"""Repository for candidate fix evaluations with price tags."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.db import transaction
from agentbreak.schemas.fix import FixEval, FixEvalDetails, FixSpec, PriceTag


class FixRepo:
    """SQLite data access for fix evaluations."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, fix_eval: FixEval) -> FixEval:
        """Insert a new fix evaluation record."""
        sql = """
        INSERT INTO fix_eval (
            id, audit_id, target_id, base_policy_id, fix_json,
            result_policy_id, trials, status, attacks_total, attacks_blocked,
            benign_total, benign_broken, pareto, details_json, retest_of,
            created_at, finished_at
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?
        );
        """
        pt = fix_eval.price_tag
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    fix_eval.id,
                    fix_eval.audit_id,
                    fix_eval.target_id,
                    fix_eval.base_policy_id,
                    json.dumps(fix_eval.fix.model_dump()),
                    fix_eval.result_policy_id,
                    fix_eval.trials,
                    fix_eval.status,
                    pt.attacks_total if pt else None,
                    pt.attacks_blocked if pt else None,
                    pt.benign_total if pt else None,
                    pt.tasks_broken if pt else None,
                    1 if (pt and pt.pareto) else 0,
                    json.dumps(fix_eval.details.model_dump()) if fix_eval.details else None,
                    fix_eval.retest_of,
                    fix_eval.created_at,
                    fix_eval.finished_at,
                ),
            )
        return fix_eval

    def update(self, fix_eval: FixEval) -> FixEval:
        """Update an existing fix evaluation record."""
        sql = """
        UPDATE fix_eval
        SET status = ?, attacks_total = ?, attacks_blocked = ?, benign_total = ?,
            benign_broken = ?, pareto = ?, details_json = ?, result_policy_id = ?, finished_at = ?
        WHERE id = ?;
        """
        pt = fix_eval.price_tag
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    fix_eval.status,
                    pt.attacks_total if pt else None,
                    pt.attacks_blocked if pt else None,
                    pt.benign_total if pt else None,
                    pt.tasks_broken if pt else None,
                    1 if (pt and pt.pareto) else 0,
                    json.dumps(fix_eval.details.model_dump()) if fix_eval.details else None,
                    fix_eval.result_policy_id,
                    fix_eval.finished_at,
                    fix_eval.id,
                ),
            )
        return fix_eval

    def get(self, eval_id: str) -> FixEval | None:
        """Retrieve fix evaluation by ID."""
        sql = """
        SELECT id, audit_id, target_id, base_policy_id, fix_json,
               result_policy_id, trials, status, attacks_total, attacks_blocked,
               benign_total, benign_broken, pareto, details_json, retest_of,
               created_at, finished_at
        FROM fix_eval
        WHERE id = ?;
        """
        row = self.conn.execute(sql, (eval_id,)).fetchone()
        if not row:
            return None
        return self._row_to_model(row)

    def list_evals(
        self,
        target_id: str | None = None,
        audit_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FixEval]:
        """List fix evaluations with optional filters."""
        conditions: list[str] = []
        params: list[object] = []

        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)
        if audit_id:
            conditions.append("audit_id = ?")
            params.append(audit_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
        SELECT id, audit_id, target_id, base_policy_id, fix_json,
               result_policy_id, trials, status, attacks_total, attacks_blocked,
               benign_total, benign_broken, pareto, details_json, retest_of,
               created_at, finished_at
        FROM fix_eval
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_model(r) for r in rows]

    def count_evals(
        self,
        target_id: str | None = None,
        audit_id: str | None = None,
    ) -> int:
        """Count total fix evaluations."""
        conditions: list[str] = []
        params: list[object] = []

        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)
        if audit_id:
            conditions.append("audit_id = ?")
            params.append(audit_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT COUNT(*) FROM fix_eval {where_clause};"
        return int(self.conn.execute(sql, params).fetchone()[0])

    def _row_to_model(self, row: sqlite3.Row | tuple[Any, ...]) -> FixEval:
        fix_data = json.loads(row[4])
        pt = None
        if row[8] is not None:
            pt = PriceTag(
                attacks_total=row[8],
                attacks_blocked=row[9],
                benign_total=row[10],
                tasks_broken=row[11],
                pareto=bool(row[12]),
            )
        details = FixEvalDetails.model_validate(json.loads(row[13])) if row[13] else None

        return FixEval(
            id=row[0],
            audit_id=row[1],
            target_id=row[2],
            base_policy_id=row[3],
            fix=FixSpec.model_validate(fix_data),
            result_policy_id=row[5],
            trials=row[6],
            status=row[7],
            price_tag=pt,
            details=details,
            retest_of=row[14],
            created_at=row[15],
            finished_at=row[16],
        )
