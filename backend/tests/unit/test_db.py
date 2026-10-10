"""Unit tests for SQLite database layer, migrations, and repository operations."""

import sqlite3

import pytest
from agentbreak.db import get_connection, migrate, new_id
from agentbreak.repo import PolicyRepo, RunRepo, TargetRepo
from agentbreak.schemas.policy import Grant, Policy
from agentbreak.schemas.run import Run, TraceStep
from agentbreak.schemas.target import Target


@pytest.fixture
def db_conn():
    """Create an in-memory database with schema migrated."""
    conn = get_connection(":memory:")
    migrate(conn)
    yield conn
    conn.close()


def test_migration_is_idempotent(db_conn):
    """Test user_version is 1 and subsequent migrations are no-ops."""
    cur = db_conn.cursor()
    cur.execute("PRAGMA user_version;")
    version = cur.fetchone()[0]
    assert version == 1

    # Second migration call
    version_after = migrate(db_conn)
    assert version_after == 1


def test_target_repo_roundtrip(db_conn):
    """Test target create, read, and list operations."""
    repo = TargetRepo(db_conn)
    target = Target(
        id=new_id("tgt"),
        name="test-scripted",
        kind="scripted",
        config={"profile": "gullible"},
        active_policy_id=None,
        created_at="2026-10-10T12:00:00Z",
    )
    repo.create(target)

    fetched = repo.get(target.id)
    assert fetched is not None
    assert fetched.id == target.id
    assert fetched.name == "test-scripted"
    assert fetched.config == {"profile": "gullible"}

    all_targets = repo.list()
    assert len(all_targets) == 1
    assert all_targets[0].id == target.id


def test_policy_repo_roundtrip(db_conn):
    """Test policy creation and retrieval by ID and canonical hash."""
    repo = PolicyRepo(db_conn)
    policy = Policy(
        id=new_id("pol"),
        name="Full Access",
        parent_id=None,
        grants=[
            Grant(tool="read_email", constraints=[]),
            Grant(tool="send_email", constraints=[]),
        ],
        hash="sha256:dummyhash123",
        created_at="2026-10-10T12:00:00Z",
    )
    repo.create(policy)

    fetched = repo.get(policy.id)
    assert fetched is not None
    assert fetched.id == policy.id
    assert len(fetched.grants) == 2
    assert fetched.grants[0].tool == "read_email"

    by_hash = repo.get_by_hash("sha256:dummyhash123")
    assert by_hash is not None
    assert by_hash.id == policy.id


def test_foreign_key_violation_raises(db_conn):
    """Test foreign key constraint enforcement in SQLite."""
    run_repo = RunRepo(db_conn)
    invalid_run = Run(
        id=new_id("run"),
        kind="attack",
        target_id="non_existent_target",
        policy_id="non_existent_policy",
        suite="acme",
        user_task_id="BT-01",
        status="queued",
        repro={},
        created_at="2026-10-10T12:00:00Z",
    )

    with pytest.raises(sqlite3.IntegrityError):
        run_repo.create(invalid_run)


def test_cascade_delete_run(db_conn):
    """Test that deleting a run cascades to its trace steps and snapshots."""
    target_repo = TargetRepo(db_conn)
    policy_repo = PolicyRepo(db_conn)
    run_repo = RunRepo(db_conn)

    target = target_repo.create(
        Target(
            id=new_id("tgt"),
            name="demo-target",
            kind="scripted",
            config={},
            created_at="2026-10-10T12:00:00Z",
        )
    )
    policy = policy_repo.create(
        Policy(
            id=new_id("pol"),
            name="demo-policy",
            grants=[],
            hash="sha256:test",
            created_at="2026-10-10T12:00:00Z",
        )
    )

    run = run_repo.create(
        Run(
            id=new_id("run"),
            kind="attack",
            target_id=target.id,
            policy_id=policy.id,
            suite="acme",
            user_task_id="BT-01",
            status="done",
            repro={"seed": 42},
            created_at="2026-10-10T12:00:00Z",
        )
    )

    # Add trace step and snapshot
    run_repo.add_trace_step(
        run.id,
        TraceStep(idx=0, role="system", kind="system", content="init"),
    )
    run_repo.save_snapshot(run.id, "pre", {"inbox": ["e-1001"]})
    run_repo.save_snapshot(run.id, "post", {"inbox": ["e-1001"]})

    # Verify trace and snapshots exist
    assert len(run_repo.get_trace(run.id)) == 1
    assert run_repo.get_snapshots(run.id) is not None

    # Delete run
    deleted = run_repo.delete(run.id)
    assert deleted is True

    # Assert cascade: trace steps and snapshots should be gone
    assert len(run_repo.get_trace(run.id)) == 0
    assert run_repo.get_snapshots(run.id) is None
