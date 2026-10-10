"""Discovery repository for autonomous campaign tracking and attempts."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentbreak.schemas.discovery import DiscoveryAttempt, DiscoveryCampaign


class DiscoveryRepo:
    """Repository handling CRUD operations for discovery campaigns and attempts."""

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
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO discovery_campaign (
                id, target_id, policy_id, scenario_ids_json, budget_json,
                seed, use_attacker_llm, status, attempts, successes, coverage_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                target_id,
                policy_id,
                json.dumps(scenario_ids),
                json.dumps(budget),
                seed,
                1 if use_attacker_llm else 0,
                "queued",
                0,
                0,
                json.dumps({}),
                created_at,
            ),
        )
        self.conn.commit()
        camp = self.get_campaign(campaign_id)
        if camp is None:
            raise RuntimeError(f"Failed to create campaign '{campaign_id}'.")
        return camp

    def get_campaign(self, campaign_id: str) -> DiscoveryCampaign | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, target_id, policy_id, status, attempts, successes,
                   coverage_json, created_at, finished_at
            FROM discovery_campaign
            WHERE id = ?
            """,
            (campaign_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Fetch attempts list
        cursor.execute(
            """
            SELECT n, case_id, fingerprint, origin, mutation_chain_json, run_id, success
            FROM discovery_attempt
            WHERE campaign_id = ?
            ORDER BY n ASC
            """,
            (campaign_id,),
        )
        attempt_rows = cursor.fetchall()
        attempts_list = [
            DiscoveryAttempt(
                n=a[0],
                case_id=a[1],
                fingerprint=a[2],
                origin=a[3],
                mutation_chain=json.loads(a[4] or "[]"),
                run_id=a[5],
                success=bool(a[6]),
            )
            for a in attempt_rows
        ]

        return DiscoveryCampaign(
            id=row[0],
            target_id=row[1],
            policy_id=row[2],
            status=row[3],
            attempts=row[4],
            successes=row[5],
            coverage=json.loads(row[6] or "{}"),
            attempts_list=attempts_list,
            created_at=row[7],
            finished_at=row[8],
        )

    def list_campaigns(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[DiscoveryCampaign], int]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM discovery_campaign")
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT id FROM discovery_campaign ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cursor.fetchall()
        items: list[DiscoveryCampaign] = []
        for r in rows:
            camp = self.get_campaign(r[0])
            if camp:
                items.append(camp)
        return items, total

    def add_attempt(
        self,
        campaign_id: str,
        n: int,
        case_id: str,
        fingerprint: str,
        origin: str,
        mutation_chain: list[str],
        run_id: str | None,
        success: bool,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO discovery_attempt (
                campaign_id, n, case_id, fingerprint, origin,
                mutation_chain_json, run_id, success
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                n,
                case_id,
                fingerprint,
                origin,
                json.dumps(mutation_chain),
                run_id,
                1 if success else 0,
            ),
        )
        self.conn.commit()

    def update_campaign_status(
        self,
        campaign_id: str,
        status: str,
        attempts: int,
        successes: int,
        coverage: dict[str, Any],
        finished_at: str | None = None,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE discovery_campaign
            SET status = ?,
                attempts = ?,
                successes = ?,
                coverage_json = ?,
                finished_at = ?
            WHERE id = ?
            """,
            (status, attempts, successes, json.dumps(coverage), finished_at, campaign_id),
        )
        self.conn.commit()
