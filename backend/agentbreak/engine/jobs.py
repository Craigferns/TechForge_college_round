"""Background execution job pool and process lifecycle manager."""

from __future__ import annotations

import concurrent.futures
import datetime
import logging
import sqlite3
import threading
from typing import Any

from agentbreak.config import get_settings
from agentbreak.db import get_connection, transaction
from agentbreak.engine.runner import execute_run

logger = logging.getLogger(__name__)


class JobPool:
    """ThreadPoolExecutor-backed background execution pool with cancellation and crash recovery."""

    def __init__(self, max_workers: int | None = None) -> None:
        settings = get_settings()
        self.max_workers = max_workers or settings.max_workers
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        self._futures: dict[str, concurrent.futures.Future[Any]] = {}
        self._cancel_flags: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def submit_run(self, run_id: str, timeout_s: float | None = None) -> None:
        """Submit an evaluation run for asynchronous execution."""
        cancel_evt = threading.Event()
        with self._lock:
            if self._executor._shutdown:
                self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
            self._cancel_flags[run_id] = cancel_evt

            def _worker() -> None:
                if cancel_evt.is_set():
                    return
                execute_run(run_id)

            future = self._executor.submit(_worker)
            self._futures[run_id] = future

            def _done_callback(fut: concurrent.futures.Future[Any]) -> None:
                with self._lock:
                    self._futures.pop(run_id, None)
                    self._cancel_flags.pop(run_id, None)

            future.add_done_callback(_done_callback)

    def cancel_run(self, run_id: str, conn: sqlite3.Connection | None = None) -> bool:
        """Cancel an active or queued run and mark its status as cancelled."""
        with self._lock:
            if run_id in self._cancel_flags:
                self._cancel_flags[run_id].set()

            fut = self._futures.get(run_id)
            if fut is not None:
                fut.cancel()

        settings = get_settings()
        owns_conn = conn is None
        active_conn = conn if conn is not None else get_connection(settings.db_path)
        try:
            now = datetime.datetime.now(datetime.UTC).isoformat()
            with transaction(active_conn):
                cur = active_conn.execute(
                    """
                    UPDATE run
                    SET status = 'cancelled', finished_at = ?
                    WHERE id = ? AND status IN ('queued', 'running');
                    """,
                    (now, run_id),
                )
                return cur.rowcount > 0
        finally:
            if owns_conn:
                active_conn.close()

    def startup_recovery(self, conn: sqlite3.Connection) -> int:
        """Recover runs and sleeper runs left in 'running' state from previous process crashes."""
        now = datetime.datetime.now(datetime.UTC).isoformat()
        recovered = 0
        with transaction(conn):
            cur = conn.execute(
                """
                UPDATE run
                SET status = 'error', error = 'error: interrupted', finished_at = ?
                WHERE status = 'running';
                """,
                (now,),
            )
            recovered += cur.rowcount

            cur_sleeper = conn.execute(
                """
                UPDATE sleeper_run
                SET status = 'error', finished_at = ?
                WHERE status = 'running';
                """,
                (now,),
            )
            recovered += cur_sleeper.rowcount

        if recovered > 0:
            logger.warning("Startup recovery transitioned %d interrupted runs to error.", recovered)
        return recovered

    def shutdown(self, wait: bool = False) -> None:
        """Shut down the underlying thread pool executor."""
        with self._lock:
            for evt in self._cancel_flags.values():
                evt.set()
        self._executor.shutdown(wait=wait, cancel_futures=True)


_GLOBAL_JOB_POOL: JobPool | None = None
_JOB_POOL_LOCK = threading.Lock()


def get_job_pool() -> JobPool:
    """Return the global process JobPool singleton."""
    global _GLOBAL_JOB_POOL
    with _JOB_POOL_LOCK:
        if _GLOBAL_JOB_POOL is None:
            _GLOBAL_JOB_POOL = JobPool()
        return _GLOBAL_JOB_POOL


def reset_job_pool() -> None:
    """Reset the global JobPool (primarily for testing)."""
    global _GLOBAL_JOB_POOL
    with _JOB_POOL_LOCK:
        if _GLOBAL_JOB_POOL is not None:
            _GLOBAL_JOB_POOL.shutdown(wait=False)
            _GLOBAL_JOB_POOL = None
