"""One-click demo orchestrator (PLAN.md §10.3 / SM-1).

Every stage detail is computed from the runs it executes; nothing is pre-written.
Scope: the demo only touches the simulated demo target `tgt_demo_scripted`.
"""

from __future__ import annotations

import datetime
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from agentbreak.config import get_settings
from agentbreak.db import get_connection
from agentbreak.domain.report import generate_markdown_report
from agentbreak.engine.audit import execute_permission_audit
from agentbreak.engine.fixes import apply_fix_eval, evaluate_fix, suggest_fixes
from agentbreak.engine.measure import ATTACK_MATRIX, BENIGN_IDS, SLEEPER_CASE, measure_policy
from agentbreak.engine.runner import execute_run
from agentbreak.engine.sleeper import execute_sleeper_run
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.fix_repo import FixRepo
from agentbreak.repo.report_repo import ReportRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.repo.target_repo import TargetRepo
from agentbreak.schemas.audit import AuditCreate
from agentbreak.schemas.dashboard import DemoLinks, DemoStage, DemoStatus
from agentbreak.schemas.fix import FixEvalCreate
from agentbreak.schemas.run import Run
from agentbreak.schemas.sleeper import SleeperRunCreate
from agentbreak.seed import seed_database
from agentbreak.targets.scripted import ScriptedTarget

DEMO_TARGET = "tgt_demo_scripted"
DEMO_BASE_POLICY = "pol_full"


def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


# Demo status cache for polling (process-local).
DEMO_RUNS_CACHE: dict[str, DemoStatus] = {}

_STAGES = [
    ("seed", "Reset & seed", "Reset the simulated demo target to the full-access policy"),
    ("attacks", "Attack evaluation", "Run attack cases AS-01..07 under the full policy"),
    ("benign", "Benign ground truth", "Run benign tasks BT-01..10 under the full policy"),
    ("audit", "Permission audit", "Counterfactual re-runs: which tool enables which exploit"),
    (
        "fixes",
        "Fix price tags",
        "Measure each evidence-derived fix against attacks and benign tasks",
    ),
    ("remediate", "Apply & verify", "Apply Pareto-optimal fixes one by one, then re-measure"),
    ("report", "Evidence report", "Generate the Markdown evidence report"),
]


# One demo at a time: concurrent demos would race on the demo target's active policy.
_DEMO_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="demo")
_DEMO_LOCK = threading.Lock()


def start_demo() -> DemoStatus:
    """Start the demo in the background (or return the one already running); poll GET /demo/{id}."""
    with _DEMO_LOCK:
        running = next(
            (d for d in DEMO_RUNS_CACHE.values() if d.status in ("queued", "running")), None
        )
        if running is not None:
            return running
        d_id = f"demo_{uuid.uuid4().hex[:8]}"
        st = DemoStatus(
            id=d_id,
            status="queued",
            stage="Queued",
            stages=[DemoStage(id=i, name=n, status="pending", detail=d) for i, n, d in _STAGES],
        )
        DEMO_RUNS_CACHE[d_id] = st
        _DEMO_POOL.submit(run_full_demo, d_id)
        return st


def run_full_demo(demo_id: str | None = None, conn: sqlite3.Connection | None = None) -> DemoStatus:
    owns_conn = conn is None
    db = conn if conn is not None else get_connection(get_settings().db_path)
    d_id = demo_id or f"demo_{uuid.uuid4().hex[:8]}"
    stages = [DemoStage(id=i, name=n, status="pending", detail=d) for i, n, d in _STAGES]
    st = DemoStatus(id=d_id, status="running", stage=stages[0].name, stages=stages)
    DEMO_RUNS_CACHE[d_id] = st
    target = ScriptedTarget()
    current = 0

    def begin(idx: int) -> None:
        nonlocal current
        current = idx
        stages[idx].status = "running"
        st.stage = stages[idx].name

    def done(idx: int, detail: str) -> None:
        stages[idx].status = "completed"
        stages[idx].detail = detail

    try:
        # 1. Reset only the demo target: full policy again, its findings reopened.
        begin(0)
        seed_database(db)
        TargetRepo(db).update_active_policy(DEMO_TARGET, DEMO_BASE_POLICY)
        db.execute(
            "UPDATE finding SET status = 'open' WHERE target_id = ? AND status != 'open'",
            (DEMO_TARGET,),
        )
        db.commit()
        done(0, f"Target '{DEMO_TARGET}' (simulated) reset to policy '{DEMO_BASE_POLICY}'.")

        # 2. Attacks: persisted single runs (for trace pages) + the sleeper chain.
        begin(1)
        run_repo = RunRepo(db)
        attack_runs: dict[str, Run] = {}
        for case_id, scenario_id, carrier, inj in ATTACK_MATRIX:
            run = Run(
                id=f"run_{d_id}_{case_id.lower()}",
                kind="attack",
                target_id=DEMO_TARGET,
                policy_id=DEMO_BASE_POLICY,
                suite="acme",
                case_id=case_id,
                scenario_id=scenario_id,
                user_task_id=carrier,
                injection_task_id=inj,
                status="queued",
                repro={"demo_id": d_id},
                created_at=utc_now_iso(),
            )
            run_repo.create(run)
            attack_runs[case_id] = execute_run(run.id, conn=db, target_override=target)
        sleeper = execute_sleeper_run(
            SleeperRunCreate(
                target_id=DEMO_TARGET, policy_id=DEMO_BASE_POLICY, case_id=SLEEPER_CASE
            ),
            conn=db,
            target_override=target,
        )
        single = [c for c, r in attack_runs.items() if c != SLEEPER_CASE and r.security is True]
        errored = [c for c, r in attack_runs.items() if r.status != "done"]
        exploited = len(single) + (1 if sleeper.outcome == "triggered" else 0)
        sev = [r.verdict.severity for r in attack_runs.values() if r.verdict and r.verdict.success]
        done(
            1,
            f"{exploited}/{len(ATTACK_MATRIX)} attacks confirmed by state diff "
            f"({sev.count('critical')} critical, {sev.count('high')} high); "
            f"sleeper outcome: {sleeper.outcome}"
            + (f"; errored: {', '.join(errored)}" if errored else ""),
        )

        # 3. Benign ground truth.
        begin(2)
        passed = 0
        for task_id in BENIGN_IDS:
            run = Run(
                id=f"run_{d_id}_{task_id.lower()}",
                kind="benign",
                target_id=DEMO_TARGET,
                policy_id=DEMO_BASE_POLICY,
                suite="acme",
                user_task_id=task_id,
                status="queued",
                repro={"demo_id": d_id},
                created_at=utc_now_iso(),
            )
            run_repo.create(run)
            if execute_run(run.id, conn=db, target_override=target).utility is True:
                passed += 1
        done(2, f"{passed}/{len(BENIGN_IDS)} benign tasks pass under the full policy.")

        # 4. Audit.
        begin(3)
        audit = execute_permission_audit(
            AuditCreate(target_id=DEMO_TARGET, policy_id=DEMO_BASE_POLICY),
            conn=db,
            target_override=target,
        )
        if audit.status != "done":
            raise RuntimeError(f"Audit {audit.id} failed: {audit.stage}")
        proof = audit.proof
        done(
            3,
            f"Granted {len(audit.granted)}, needed {len(audit.needed)}, excess "
            f"{len(audit.excess)} ({', '.join(audit.excess) or 'none'}); minimal policy keeps "
            f"{proof.benign_pass_under_minimal if proof else 0}/{proof.benign_total if proof else 0} "
            "benign tasks passing.",
        )

        # 5. Price tags for every evidence-derived suggestion, against the full policy.
        begin(4)
        evals = [
            evaluate_fix(
                FixEvalCreate(target_id=DEMO_TARGET, base_policy_id=DEMO_BASE_POLICY, fix=s.fix),
                audit_id=audit.id,
                conn=db,
                target_override=target,
            )
            for s in suggest_fixes(audit)
        ]
        evals = [e for e in (FixRepo(db).get(e.id) for e in evals) if e is not None]  # fresh Pareto
        pareto = [e for e in evals if e.price_tag and e.price_tag.pareto]
        done(4, f"{len(evals)} fixes measured; {len(pareto)} Pareto-optimal.")

        # 6. Remediation chain: apply each Pareto fix that breaks nothing, re-measured on the
        #    policy produced by the previous step (fixes stack), then verify the final policy.
        begin(5)
        policy_id = DEMO_BASE_POLICY
        applied: list[str] = []
        for e in pareto:
            if e.price_tag is None or e.price_tag.tasks_broken != 0:
                continue
            step = evaluate_fix(
                FixEvalCreate(target_id=DEMO_TARGET, base_policy_id=policy_id, fix=e.fix),
                audit_id=audit.id,
                conn=db,
                target_override=target,
            )
            if step.price_tag is None or step.price_tag.tasks_broken != 0:
                continue  # stacking changed the cost: skip rather than break legit work
            policy_id = apply_fix_eval(step.id, conn=db).id
            applied.append(f"{e.fix.kind}:{e.fix.tool}")
        final = measure_policy(
            policy_id, DEMO_TARGET, db, target, {"demo_id": d_id, "verification": True}
        )
        open_left = [
            f.case_id
            for f in FindingRepo(db).list_findings(target_id=DEMO_TARGET, limit=200)[0]
            if f.status in ("open", "regressed")
        ]
        done(
            5,
            f"Applied {len(applied)} fixes ({', '.join(applied) or 'none'}). Re-measured policy "
            f"'{policy_id}': {len(final.exploited)}/{len(ATTACK_MATRIX)} attacks succeed, "
            f"{len(final.benign_passed)}/{len(BENIGN_IDS)} benign pass, sleeper "
            f"{final.sleeper_outcome}"
            + (f", inconclusive: {sorted(final.inconclusive)}" if final.inconclusive else "")
            + (f"; still open: {', '.join(open_left)}" if open_left else "")
            + ".",
        )

        # 7. Report.
        begin(6)
        report = generate_markdown_report(
            report_id=f"rep_{uuid.uuid4().hex[:8]}",
            target_id=DEMO_TARGET,
            policy_id=policy_id,
            conn=db,
            created_at=utc_now_iso(),
        )
        ReportRepo(db).create(report)
        done(6, f"Report {report.id} generated.")

        st.status = "completed"
        st.stage = "All stages completed"
        st.links = DemoLinks(
            dashboard="/dashboard",
            run=f"/runs/run_{d_id}_as-04",
            audit=f"/permissions/{audit.id}",
            fixlab=f"/fixes/{audit.id}",
            sleeper=f"/sleeper/{sleeper.id}",
            report=f"/report/{report.id}",
        )
    except Exception as exc:  # job boundary: record, mark the failing stage, never fake success
        stages[current].status = "error"
        st.status = "error"
        st.error = f"{type(exc).__name__}: {exc}"[:500]
        st.stage = f"Failed at: {stages[current].name}"
    finally:
        if owns_conn:
            db.close()

    DEMO_RUNS_CACHE[d_id] = st
    return st
