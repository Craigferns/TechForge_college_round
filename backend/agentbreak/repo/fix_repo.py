"""Fix evaluation repository for persistence and Pareto analysis."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.schemas.fix import FixEval, FixEvalDetails, FixSpec, PriceTag


class FixRepo:
    """Repository handling CRUD and queries for candidate fix evaluations."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, fix_eval: FixEval) -> FixEval:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO fix_eval (
                id, audit_id, target_id, base_policy_id, fix_json, result_policy_id,
                trials, status, attacks_total, attacks_blocked, benign_total,
                benign_broken, pareto, details_json, created_at, finished_at, retest_of
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fix_eval.id,
                fix_eval.audit_id,
                fix_eval.target_id,
                fix_eval.base_policy_id,
                json.dumps(fix_eval.fix.model_dump()),
                fix_eval.result_policy_id,
                fix_eval.trials,
                fix_eval.status,
                fix_eval.price_tag.attacks_total if fix_eval.price_tag else 0,
                fix_eval.price_tag.attacks_blocked if fix_eval.price_tag else 0,
                fix_eval.price_tag.benign_total if fix_eval.price_tag else 0,
                fix_eval.price_tag.tasks_broken if fix_eval.price_tag else 0,
                1 if (fix_eval.price_tag and fix_eval.price_tag.pareto) else 0,
                json.dumps(fix_eval.details.model_dump()) if fix_eval.details else json.dumps({}),
                fix_eval.created_at,
                fix_eval.finished_at,
                fix_eval.retest_of,
            ),
        )
        self.conn.commit()
        return fix_eval

    def set_pareto(self, fix_eval_id: str, pareto: bool) -> None:
        self.conn.execute(
            "UPDATE fix_eval SET pareto = ? WHERE id = ?", (1 if pareto else 0, fix_eval_id)
        )
        self.conn.commit()

    def get(self, fix_eval_id: str) -> FixEval | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, audit_id, target_id, base_policy_id, fix_json, result_policy_id,
                   trials, status, attacks_total, attacks_blocked, benign_total,
                   benign_broken, pareto, details_json, created_at, finished_at, retest_of
            FROM fix_eval
            WHERE id = ?
            """,
            (fix_eval_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        fix_spec = FixSpec.model_validate(json.loads(row[4]))
        price_tag = PriceTag(
            attacks_total=row[8] or 0,
            attacks_blocked=row[9] or 0,
            benign_total=row[10] or 0,
            tasks_broken=row[11] or 0,
            pareto=bool(row[12]),
        )
        details = FixEvalDetails.model_validate(json.loads(row[13] or "{}"))

        return FixEval(
            id=row[0],
            audit_id=row[1],
            target_id=row[2],
            base_policy_id=row[3],
            fix=fix_spec,
            result_policy_id=row[5],
            trials=row[6],
            status=row[7],
            price_tag=price_tag,
            details=details,
            created_at=row[14],
            finished_at=row[15],
            retest_of=row[16],
        )

    def list(
        self,
        audit_id: str | None = None,
        target_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FixEval], int]:
        cursor = self.conn.cursor()
        conds = []
        params: list[Any] = []
        if audit_id:
            conds.append("audit_id = ?")
            params.append(audit_id)
        if target_id:
            conds.append("target_id = ?")
            params.append(target_id)
        where = f"WHERE {' AND '.join(conds)}" if conds else ""

        cursor.execute(f"SELECT COUNT(*) FROM fix_eval {where}", params)
        total = cursor.fetchone()[0]

        cursor.execute(
            f"SELECT id FROM fix_eval {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        rows = cursor.fetchall()
        items: list[FixEval] = []
        for r in rows:
            fe = self.get(r[0])
            if fe:
                items.append(fe)
        return items, total
