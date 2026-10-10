"""Run, trace, snapshot, and verdict repository."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.db import transaction
from agentbreak.schemas.run import Run, RunSummary, SnapshotPair, TraceStep, Verdict


class RunRepo:
    """Data access layer for runs, tool traces, environment snapshots, and verdicts."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        if self.conn.row_factory is None:
            self.conn.row_factory = sqlite3.Row

    def create(self, run: Run) -> Run:
        """Insert a new evaluation run record."""
        sql = """
        INSERT INTO run (
            id, kind, target_id, policy_id, suite, case_id, scenario_id,
            user_task_id, injection_task_id, template_id, payload_text, payload_hash,
            origin, status, error, utility, security, model_output, repro_json,
            created_at, started_at, finished_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?
        );
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    run.id,
                    run.kind,
                    run.target_id,
                    run.policy_id,
                    run.suite,
                    run.case_id,
                    run.scenario_id,
                    run.user_task_id,
                    run.injection_task_id,
                    run.template_id,
                    run.payload_text,
                    run.payload_hash,
                    run.origin,
                    run.status,
                    run.error,
                    1 if run.utility else (0 if run.utility is False else None),
                    1 if run.security else (0 if run.security is False else None),
                    run.model_output,
                    json.dumps(run.repro),
                    run.created_at,
                    run.started_at,
                    run.finished_at,
                ),
            )
            if run.verdict:
                self.save_verdict(run.id, run.verdict)

        return run

    def get(self, run_id: str) -> Run | None:
        """Fetch full run details with its associated verdict if available."""
        sql = "SELECT * FROM run WHERE id = ?;"
        cursor = self.conn.cursor()
        cursor.execute(sql, (run_id,))
        row = cursor.fetchone()
        if not row:
            return None

        verdict = self.get_verdict(run_id)
        return self._row_to_run(row, verdict)

    def list_runs(
        self,
        target_id: str | None = None,
        policy_id: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        scenario_id: str | None = None,
        case_id: str | None = None,
        ids: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RunSummary]:
        """List runs with summary projections and optional filters."""
        clauses = []
        params: list[Any] = []

        if target_id:
            clauses.append("r.target_id = ?")
            params.append(target_id)
        if policy_id:
            clauses.append("r.policy_id = ?")
            params.append(policy_id)
        if kind:
            clauses.append("r.kind = ?")
            params.append(kind)
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        if scenario_id:
            clauses.append("r.scenario_id = ?")
            params.append(scenario_id)
        if case_id:
            clauses.append("r.case_id = ?")
            params.append(case_id)
        if ids:
            placeholders = ",".join("?" for _ in ids)
            clauses.append(f"r.id IN ({placeholders})")
            params.extend(ids)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
        SELECT
            r.id, r.kind, r.target_id, r.policy_id, r.suite, r.case_id, r.scenario_id,
            r.user_task_id, r.status, r.utility, r.security, r.created_at, r.finished_at,
            v.success AS verdict_success, v.severity AS verdict_severity
        FROM run r
        LEFT JOIN verdict v ON r.id = v.run_id
        {where_clause}
        ORDER BY r.created_at DESC
        LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        summaries = []
        for r in rows:
            summaries.append(
                RunSummary(
                    id=r["id"],
                    kind=r["kind"],
                    target_id=r["target_id"],
                    policy_id=r["policy_id"],
                    suite=r["suite"],
                    case_id=r["case_id"],
                    scenario_id=r["scenario_id"],
                    user_task_id=r["user_task_id"],
                    status=r["status"],
                    utility=bool(r["utility"]) if r["utility"] is not None else None,
                    security=bool(r["security"]) if r["security"] is not None else None,
                    verdict_success=bool(r["verdict_success"])
                    if r["verdict_success"] is not None
                    else None,
                    severity=r["verdict_severity"],
                    created_at=r["created_at"],
                    finished_at=r["finished_at"],
                )
            )
        return summaries

    def count_runs(
        self,
        target_id: str | None = None,
        policy_id: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        scenario_id: str | None = None,
        case_id: str | None = None,
        ids: list[str] | None = None,
    ) -> int:
        """Count total runs matching filter criteria."""
        clauses = []
        params: list[Any] = []

        if target_id:
            clauses.append("r.target_id = ?")
            params.append(target_id)
        if policy_id:
            clauses.append("r.policy_id = ?")
            params.append(policy_id)
        if kind:
            clauses.append("r.kind = ?")
            params.append(kind)
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        if scenario_id:
            clauses.append("r.scenario_id = ?")
            params.append(scenario_id)
        if case_id:
            clauses.append("r.case_id = ?")
            params.append(case_id)
        if ids:
            placeholders = ",".join("?" for _ in ids)
            clauses.append(f"r.id IN ({placeholders})")
            params.extend(ids)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT COUNT(*) AS total FROM run r {where_clause};"
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return int(row["total"]) if row else 0

    def update_status(
        self,
        run_id: str,
        status: str,
        error: str | None = None,
        utility: bool | None = None,
        security: bool | None = None,
        model_output: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> bool:
        """Update run execution status and execution flags."""
        sql = """
        UPDATE run SET
            status = ?,
            error = COALESCE(?, error),
            utility = COALESCE(?, utility),
            security = COALESCE(?, security),
            model_output = COALESCE(?, model_output),
            started_at = COALESCE(?, started_at),
            finished_at = COALESCE(?, finished_at)
        WHERE id = ?;
        """
        u_int = 1 if utility is True else (0 if utility is False else None)
        s_int = 1 if security is True else (0 if security is False else None)
        with transaction(self.conn):
            cur = self.conn.execute(
                sql, (status, error, u_int, s_int, model_output, started_at, finished_at, run_id)
            )
            return cur.rowcount > 0

    def add_trace_step(self, run_id: str, step: TraceStep) -> TraceStep:
        """Append an execution trace step."""
        sql = """
        INSERT INTO trace_step (run_id, idx, role, kind, tool, args_json, content, flags_json, caused_by_idx)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    run_id,
                    step.idx,
                    step.role,
                    step.kind,
                    step.tool,
                    json.dumps(step.args) if step.args else None,
                    step.content,
                    json.dumps(step.flags),
                    step.caused_by_idx,
                ),
            )
        return step

    def get_trace(self, run_id: str) -> list[TraceStep]:
        """Fetch all trace steps for a run ordered by idx."""
        sql = """
        SELECT idx, role, kind, tool, args_json, content, flags_json, caused_by_idx
        FROM trace_step
        WHERE run_id = ?
        ORDER BY idx ASC;
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, (run_id,))
        rows = cursor.fetchall()
        steps = []
        for r in rows:
            steps.append(
                TraceStep(
                    idx=r["idx"],
                    role=r["role"],
                    kind=r["kind"],
                    tool=r["tool"],
                    args=json.loads(r["args_json"]) if r["args_json"] else None,
                    content=r["content"],
                    flags=json.loads(r["flags_json"]) if r["flags_json"] else {},
                    caused_by_idx=r["caused_by_idx"],
                )
            )
        return steps

    def save_snapshot(self, run_id: str, phase: str, env_data: dict[str, Any]) -> None:
        """Save PRE or POST environment snapshot."""
        sql = """
        INSERT INTO env_snapshot (run_id, phase, env_json)
        VALUES (?, ?, ?)
        ON CONFLICT (run_id, phase) DO UPDATE SET env_json = excluded.env_json;
        """
        with transaction(self.conn):
            self.conn.execute(sql, (run_id, phase, json.dumps(env_data)))

    def get_snapshots(self, run_id: str) -> SnapshotPair | None:
        """Fetch pre and post snapshots for a run."""
        sql = "SELECT phase, env_json FROM env_snapshot WHERE run_id = ?;"
        cursor = self.conn.cursor()
        cursor.execute(sql, (run_id,))
        rows = cursor.fetchall()
        snaps: dict[str, dict[str, Any]] = {}
        for r in rows:
            snaps[r["phase"]] = json.loads(r["env_json"])

        if "pre" not in snaps or "post" not in snaps:
            return None

        return SnapshotPair(pre=snaps["pre"], post=snaps["post"], diff=[])

    def save_verdict(self, run_id: str, verdict: Verdict) -> None:
        """Save deterministic verdict evaluation."""
        sql = """
        INSERT INTO verdict (
            run_id, success, classification, impact_class, severity,
            evidence_json, verifier_version, verdict_hash, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (run_id) DO UPDATE SET
            success = excluded.success,
            classification = excluded.classification,
            impact_class = excluded.impact_class,
            severity = excluded.severity,
            evidence_json = excluded.evidence_json,
            verifier_version = excluded.verifier_version,
            verdict_hash = excluded.verdict_hash,
            created_at = excluded.created_at;
        """
        evidence_data = [e.model_dump() for e in verdict.evidence]
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    run_id,
                    1 if verdict.success else 0,
                    verdict.classification,
                    verdict.impact_class,
                    verdict.severity,
                    json.dumps(evidence_data),
                    verdict.verifier_version,
                    verdict.verdict_hash,
                    verdict.created_at,
                ),
            )

    def get_verdict(self, run_id: str) -> Verdict | None:
        """Fetch verdict for a run."""
        sql = "SELECT * FROM verdict WHERE run_id = ?;"
        cursor = self.conn.cursor()
        cursor.execute(sql, (run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Verdict(
            success=bool(row["success"]),
            classification=row["classification"],
            impact_class=row["impact_class"],
            severity=row["severity"],
            evidence=json.loads(row["evidence_json"]),
            verifier_version=row["verifier_version"],
            verdict_hash=row["verdict_hash"],
            created_at=row["created_at"],
        )

    def delete(self, run_id: str) -> bool:
        """Delete run by ID. Cascades to trace steps, snapshots, and verdict."""
        sql = "DELETE FROM run WHERE id = ?;"
        with transaction(self.conn):
            cur = self.conn.execute(sql, (run_id,))
            return cur.rowcount > 0

    @staticmethod
    def _row_to_run(row: sqlite3.Row | Any, verdict: Verdict | None = None) -> Run:
        return Run(
            id=row["id"],
            kind=row["kind"],
            target_id=row["target_id"],
            policy_id=row["policy_id"],
            suite=row["suite"],
            case_id=row["case_id"],
            scenario_id=row["scenario_id"],
            user_task_id=row["user_task_id"],
            injection_task_id=row["injection_task_id"],
            template_id=row["template_id"],
            payload_text=row["payload_text"],
            payload_hash=row["payload_hash"],
            origin=row["origin"],
            status=row["status"],
            error=row["error"],
            utility=bool(row["utility"]) if row["utility"] is not None else None,
            security=bool(row["security"]) if row["security"] is not None else None,
            model_output=row["model_output"],
            verdict=verdict,
            repro=json.loads(row["repro_json"]),
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )

    # Alias for uniform repo.list() access
    list = list_runs
