"""SQLite repository for discovery campaigns and attempts."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.db import transaction
from agentbreak.schemas.discovery import DiscoveryAttempt, DiscoveryCampaign


class DiscoveryRepo:
    """Repository managing discovery_campaign and discovery_attempt tables."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_campaign(
        self,
        campaign_id: str,
        target_id: str,
        policy_id: str,
        scenario_ids: list[str],
        budget: dict[str, Any],
        seed: int,
        use_attacker_llm: bool,
        created_at: str,
    ) -> DiscoveryCampaign:
        """Create a new discovery campaign record."""
        sql = """
        INSERT INTO discovery_campaign (
            id, target_id, policy_id, scenario_ids_json, budget_json,
            seed, use_attacker_llm, status, attempts, successes,
            coverage_json, created_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'running', 0, 0, '{}', ?, NULL);
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    campaign_id,
                    target_id,
                    policy_id,
                    json.dumps(scenario_ids),
                    json.dumps(budget),
                    seed,
                    1 if use_attacker_llm else 0,
                    created_at,
                ),
            )

        return self.get_campaign(campaign_id) or DiscoveryCampaign(
            id=campaign_id,
            target_id=target_id,
            policy_id=policy_id,
            status="running",
            attempts=0,
            successes=0,
            coverage={},
            attempts_list=[],
            created_at=created_at,
        )

    def get_campaign(self, campaign_id: str) -> DiscoveryCampaign | None:
        """Fetch campaign by ID with associated attempts list."""
        sql = "SELECT * FROM discovery_campaign WHERE id = ?;"
        cursor = self.conn.cursor()
        cursor.execute(sql, (campaign_id,))
        row = cursor.fetchone()
        if not row:
            return None

        attempts = self.get_attempts(campaign_id)
        coverage_data = json.loads(row["coverage_json"]) if row["coverage_json"] else {}

        return DiscoveryCampaign(
            id=row["id"],
            target_id=row["target_id"],
            policy_id=row["policy_id"],
            status=row["status"],
            attempts=row["attempts"],
            successes=row["successes"],
            coverage=coverage_data,
            attempts_list=attempts,
            created_at=row["created_at"],
            finished_at=row["finished_at"],
        )

    def list_campaigns(self, limit: int = 50, offset: int = 0) -> list[DiscoveryCampaign]:
        """List discovery campaigns ordered by created_at DESC."""
        sql = "SELECT id FROM discovery_campaign ORDER BY created_at DESC LIMIT ? OFFSET ?;"
        cursor = self.conn.cursor()
        cursor.execute(sql, (limit, offset))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            c = self.get_campaign(r["id"])
            if c:
                result.append(c)
        return result

    def count_campaigns(self) -> int:
        """Total number of campaigns."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM discovery_campaign;")
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    def update_campaign(
        self,
        campaign_id: str,
        status: str,
        attempts: int,
        successes: int,
        coverage: dict[str, Any],
        finished_at: str | None = None,
    ) -> None:
        """Update campaign completion metrics."""
        sql = """
        UPDATE discovery_campaign SET
            status = ?,
            attempts = ?,
            successes = ?,
            coverage_json = ?,
            finished_at = COALESCE(?, finished_at)
        WHERE id = ?;
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    status,
                    attempts,
                    successes,
                    json.dumps(coverage),
                    finished_at,
                    campaign_id,
                ),
            )

    def add_attempt(self, campaign_id: str, attempt: DiscoveryAttempt) -> None:
        """Record an attempt within a campaign."""
        sql = """
        INSERT OR IGNORE INTO discovery_attempt (
            campaign_id, n, case_id, fingerprint, origin,
            mutation_chain_json, run_id, success
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        with transaction(self.conn):
            self.conn.execute(
                sql,
                (
                    campaign_id,
                    attempt.n,
                    attempt.case_id,
                    attempt.fingerprint,
                    attempt.origin,
                    json.dumps(attempt.mutation_chain),
                    attempt.run_id,
                    1 if attempt.success else 0,
                ),
            )

    def get_attempts(self, campaign_id: str) -> list[DiscoveryAttempt]:
        """Fetch all attempts for a campaign ordered by n ASC."""
        sql = """
        SELECT n, case_id, fingerprint, origin, mutation_chain_json, run_id, success
        FROM discovery_attempt
        WHERE campaign_id = ?
        ORDER BY n ASC;
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, (campaign_id,))
        rows = cursor.fetchall()
        attempts = []
        for r in rows:
            chain = json.loads(r["mutation_chain_json"]) if r["mutation_chain_json"] else []
            attempts.append(
                DiscoveryAttempt(
                    n=r["n"],
                    case_id=r["case_id"],
                    fingerprint=r["fingerprint"],
                    origin=r["origin"],
                    mutation_chain=chain,
                    run_id=r["run_id"],
                    success=bool(r["success"]),
                )
            )
        return attempts
