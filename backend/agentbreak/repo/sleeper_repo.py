"""Repository for sleeper runs and multi-session persistence."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from agentbreak.db import transaction
from agentbreak.schemas.sleeper import SleeperRun, SleeperSession


class SleeperRepo:
    """Data access layer for multi-session sleeper runs and session timelines."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, sleeper_run: SleeperRun) -> SleeperRun:
        """Insert a new sleeper run record."""
        sql = """
        INSERT INTO sleeper_run (
            id, target_id, policy_id, case_id, gap_sessions, status, outcome, created_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    sleeper_run.id,
                    sleeper_run.target_id,
                    sleeper_run.policy_id,
                    sleeper_run.case_id,
                    sleeper_run.gap_sessions,
                    sleeper_run.status,
                    sleeper_run.outcome,
                    sleeper_run.created_at,
                    sleeper_run.finished_at,
                ),
            )
            for sess in sleeper_run.sessions:
                self.add_session(sleeper_run.id, sess)

        return sleeper_run

    def get(self, sleeper_id: str) -> SleeperRun | None:
        """Fetch sleeper run details including all associated ordered sessions."""
        sql = "SELECT * FROM sleeper_run WHERE id = ?;"
        cursor = self.conn.cursor()
        cursor.execute(sql, (sleeper_id,))
        row = cursor.fetchone()
        if not row:
            return None

        sessions = self.get_sessions(sleeper_id)
        return SleeperRun(
            id=row["id"],
            target_id=row["target_id"],
            policy_id=row["policy_id"],
            case_id=row["case_id"],
            gap_sessions=row["gap_sessions"],
            status=row["status"],
            outcome=row["outcome"],
            sessions=sessions,
            created_at=row["created_at"],
            finished_at=row["finished_at"],
        )

    def list_runs(
        self,
        target_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SleeperRun]:
        """List sleeper runs with optional target filtering."""
        clauses = []
        params: list[Any] = []
        if target_id:
            clauses.append("target_id = ?")
            params.append(target_id)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
        SELECT * FROM sleeper_run
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        runs: list[SleeperRun] = []
        for r in rows:
            sessions = self.get_sessions(r["id"])
            runs.append(
                SleeperRun(
                    id=r["id"],
                    target_id=r["target_id"],
                    policy_id=r["policy_id"],
                    case_id=r["case_id"],
                    gap_sessions=r["gap_sessions"],
                    status=r["status"],
                    outcome=r["outcome"],
                    sessions=sessions,
                    created_at=r["created_at"],
                    finished_at=r["finished_at"],
                )
            )
        return runs

    def count_runs(self, target_id: str | None = None) -> int:
        """Count total sleeper runs matching filters."""
        clauses = []
        params: list[Any] = []
        if target_id:
            clauses.append("target_id = ?")
            params.append(target_id)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT COUNT(*) AS total FROM sleeper_run {where_clause};"
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return int(row["total"]) if row else 0

    def add_session(self, sleeper_run_id: str, session: SleeperSession) -> None:
        """Insert a single session into a sleeper run."""
        sess_id = f"sess_{uuid.uuid4().hex[:12]}"
        sql = """
        INSERT INTO sleeper_session (
            id, sleeper_run_id, idx, role, run_id, memory_before_json, memory_after_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (sleeper_run_id, idx) DO UPDATE SET
            role = excluded.role,
            run_id = excluded.run_id,
            memory_before_json = excluded.memory_before_json,
            memory_after_json = excluded.memory_after_json;
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    sess_id,
                    sleeper_run_id,
                    session.idx,
                    session.role,
                    session.run_id,
                    json.dumps(session.memory_before),
                    json.dumps(session.memory_after),
                ),
            )

    def get_sessions(self, sleeper_run_id: str) -> list[SleeperSession]:
        """Fetch all sessions for a sleeper run ordered chronologically by idx."""
        sql = """
        SELECT idx, role, run_id, memory_before_json, memory_after_json
        FROM sleeper_session
        WHERE sleeper_run_id = ?
        ORDER BY idx ASC;
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, (sleeper_run_id,))
        rows = cursor.fetchall()

        sessions: list[SleeperSession] = []
        for r in rows:
            sessions.append(
                SleeperSession(
                    idx=r["idx"],
                    role=r["role"],
                    run_id=r["run_id"],
                    memory_before=json.loads(r["memory_before_json"])
                    if r["memory_before_json"]
                    else {},
                    memory_after=json.loads(r["memory_after_json"])
                    if r["memory_after_json"]
                    else {},
                )
            )
        return sessions

    def update_status(
        self,
        sleeper_id: str,
        status: str,
        outcome: str | None = None,
        finished_at: str | None = None,
    ) -> bool:
        """Update sleeper run execution state and final attack outcome."""
        sql = """
        UPDATE sleeper_run SET
            status = ?,
            outcome = COALESCE(?, outcome),
            finished_at = COALESCE(?, finished_at)
        WHERE id = ?;
        """
        with transaction(self.conn):
            cur = self.conn.execute(sql, (status, outcome, finished_at, sleeper_id))
            return cur.rowcount > 0
