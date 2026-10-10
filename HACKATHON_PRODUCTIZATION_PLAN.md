# AgentBreak — Hackathon Productization Plan

Status legend: ✅ done & verified · 🟡 partial · ⬜ not started · ⛔ out of scope.
This file is updated as work lands; the "Evidence" column says how each item was verified.

## 1. Baseline (2026-10-11, before any change in this pass)

| Check | Claimed in CLAUDE.md §6 | Actual |
|---|---|---|
| `uv run pytest` | 107/107 | 107 passed ✅ |
| `ruff check` | 0 errors | **3 errors** ❌ |
| `ruff format --check` | clean | **4 files unformatted** ❌ |
| `mypy backend/agentbreak` | 0 errors | 0 errors ✅ |
| frontend lint / typecheck / build | green | green ✅ |
| frontend tests | "passing" | **1 test total** (one smoke test) 🟡 |
| `cli demo` (documented one-command demo) | works < 60 s | **crashes on a fresh DB**: `no such table: policy` ❌ |

Working tree: phases 5–12 are uncommitted (61 changed/untracked paths). Nothing was reset or discarded.

### Correctness audit — the critical findings

The product's two headline differentiators were **not measured**:

1. **D2 fix price tags were a lookup table.** `engine/fixes.py::GOLDEN_FIX_TABLE` returned pre-written
   `attacks blocked / tasks broken` numbers; any fix not in the table showed `0/7` without running anything.
   The `pareto` flag was a heuristic (`broken == 0 or blocked > 3`), not the set-dominance rule in `domain/pricing.py`.
2. **D1 attribution was a lookup table.** `domain/attribution.py::ENABLING_MAP` hard-coded which tool enables which
   exploit, and every counterfactual returned `blocked=True` without a run. `used_by_benign` and `NEEDED_PERMISSIONS`
   were constants, not derived from what benign tasks actually did.
3. **The hard-coded tables were wrong.** Measuring for real showed e.g. removing `read_file` blocks AS-03/AS-04
   (table said AS-01/AS-02), and every benign task calls `read_memory` (table said only BT-07).
4. **Benign ground truth passed vacuously.** The scripted agent returned its canned answer even when the tool calls
   it needed were denied, so "benign task still passes" was true for read tasks under any policy.
5. **Demo stage text was hard-coded** ("7/7 attacks succeeded", "Granted 10, Needed 8") regardless of results.
6. Minor: runner swallowed finding-upsert errors (`except Exception: pass`); retest did not set `retest_of`;
   suggestions offered `defense`/`prompt_hardening` fixes that are not implemented (would "evaluate" as a no-op).

Fidelity scope, stated once: all numbers below come from the **simulated (scripted) target** on the synthetic
`acme` suite (7 attack cases, 10 benign tasks). They prove the measurement pipeline, not real-model robustness.

## 2. Preserve

Deterministic state-diff verdict engine (`domain/verdict.py`, `predicates.py`, AST purity test) · policy runtime
interposition (denied tool bodies never execute) · immutable hashed policies with parent links · SQLite run/trace/
snapshot persistence · multi-session sleeper engine · OpenAPI → generated TS types pipeline · secret/egress/fake-data scripts.

## 3. Prioritized work

| # | Pri | Item | Acceptance criteria | Effort | Status / Evidence |
|---|---|---|---|---|---|
| 1 | P0 | Fresh-DB crash | `cli demo` on an empty `data/` completes | S | ✅ `get_connection` migrates; API seeds on start; demo on fresh DB exit 0 |
| 2 | P0 | Measured fix price tags (D2) | `evaluate_fix` runs all attacks + benign under base and fixed policy; no lookup table; errors → `inconclusive`, never "blocked" | M | ✅ `engine/measure.py`; lookup table deleted; `test_price_tags_are_measured`, `test_infrastructure_errors_are_inconclusive_never_blocked` |
| 3 | P0 | Honest benign ground truth | removing a tool a task needs makes that task fail | S | ✅ scripted agent stops + reports failure on own denied call; `test_benign_task_fails_when_a_tool_it_needs_is_denied` |
| 4 | P0 | Measured attribution (D1) | needed set derived from benign traces; enabling exploits from per-tool counterfactual runs; scopes from observed benign recipients | M | ✅ counterfactual per tool; scope args from all runs, domains from passing benign; `test_audit_derives_needed_set_and_attribution_from_runs` |
| 5 | P0 | AS-05 measured end-to-end | sleeper counted exploited only if the trigger session exfiltrates | S | ✅ price tags + findings + posture use the sleeper chain outcome |
| 6 | P0 | Demo reports real numbers; remediation chain | demo applies fixes and re-measures; final posture computed, not written | M | ✅ background demo with real polling; 0/7 · 10/10 · trigger_blocked measured; `test_demo_remediation_is_measured_and_repeatable` (runs twice) |
| 7 | P0 | Lint/format gates green | ruff check + format clean | S | ✅ ruff check + format clean |
| 8 | P1 | Pareto via set dominance across sibling fixes | flag recomputed with `compute_pareto_dominance` | S | ✅ `_refresh_pareto` uses `compute_pareto_dominance` |
| 9 | P1 | No dead fix kinds | `defense`/`prompt_hardening` rejected with a clear error, not suggested | S | ✅ rejected with 422 envelope; no longer suggested |
| 10 | P1 | CI gate CLI | `cli ci` writes JSON, exit 0 pass / 1 security failure / 2 infra error | M | ✅ `cli ci` (+ `--policy-file` policy-as-code), `cli verify`; `test_ci_verify_report.py`; `docs/ci-example.yml` (commands verified locally; workflow itself not run on GitHub) |
| 11 | P1 | Ground-truth & regression tests | tests for items 2–6, 10 | M | ✅ 121 backend tests (was 107) |
| 12 | P1 | UI shows inconclusive + sleeper outcome on fix price tags | contract change → openapi → TS types → mocks | S | ✅ FixLab expandable details; contract → openapi → types → recorded mocks |
| 13 | P1 | Threat model + limitations doc | `docs/threat-model.md` | S | ✅ `docs/threat-model.md` |
| 14 | P2 | Frontend test coverage beyond one smoke test | page smoke tests per CLAUDE.md §5 | M | 🟡 7 frontend tests (was 1): route smoke tests per page incl. id routes |
| 15 | P2 | Trace explorer filtering by event type | filter chips in run detail | M | ⬜ |
| 16 | P3 | Real-model benchmark on Ollama | needs a tool-calling local model (PLAN R-03) | L | ⛔ this pass |

Dependencies: 3 → 2 → 4 → 6 (fixes and attribution are only meaningful once benign checks are honest; the demo
consumes both). 12 depends on 2. 10 depends on 2/6.

Out of scope this pass: auth/multi-tenant, distributed workers, container sandboxing of real agents, competitor
benchmarks (no fabricated comparisons), LLM-written explanations.

## 4. Demo & judging strategy

One story, all numbers live from runs: full policy → 7/7 attacks confirmed by state diff → audit shows 2 excess
tools and which tool enables which exploit (by counterfactual re-run) → fix lab price tags (blunt `remove send_email`
breaks 4 benign tasks; scoped allowlist breaks 0) → apply fixes → re-measure: 0/7 exploited, 10/10 benign pass →
sleeper timeline shows plant still lands but trigger is blocked (residual risk named, not hidden).
Talking point for "why not an LLM judge": the verdict reads only PRE/POST environment state; the scripted agent
can *say* it will exfiltrate (`says_only` profile) and the verdict stays `not exploited`.

## 5. What changed (verified 2026-10-11)

### Additional defects found and fixed while implementing
| Defect | Impact | Fix / test |
|---|---|---|
| Frontend defaulted to **mock mode** (no `.env`), so `npm run dev` and the build never called the API | the "live dashboard" showed fixtures | default `live`; `.env.mock` for `dev:mock`; header badge "Mock fixtures — not live results" |
| Landing "Run demo" was a `setInterval` animation | a prerecorded sequence presented as a live test | `POST /demo/run` starts a background job; UI polls real stage status |
| Pages fetched hard-coded fixture ids (`aud_1f3a9c02`, `rep_demo_7fa2`, `slp_demo_as05`) | every page 404'd against the real API | `useByIdOrLatest`; `/x/:id` routes the demo links to; empty/error states |
| Dashboard defaulted severity counts to 5/2 when 0; "trend projection" chart of an empty array; hard-coded captions | invented numbers | posture computed by `engine/posture.py`; fabricated elements removed |
| Report sections 3–4 hard-coded (incl. "Combined Hardening 7/7") and cited nonexistent `agentbreak verify` | fabricated evidence | report rebuilt from audits/fix evals/posture; `cli verify` implemented |
| `POST /runs/{id}/verify` returned `matches_stored=true` when snapshots were missing | a verification that never ran reported as passed | `engine/verify.py` raises → 422; `test_reverify_..._fails_closed` |
| Findings never became `regressed`; fingerprint ignored target | regressions hidden; cross-target merging | regression only on the active policy; target-scoped fingerprint; test |
| Runner swallowed finding-write errors (`except: pass`) | silent data loss | removed; error fails the run at the job boundary |
| No API error envelope although the UI expects one | every error showed as "HTTP 404" | handlers for HTTPException / ValueError / Exception (no stack traces) |
| Tests wrote into the developer's `data/agentbreak.db`; CLAUDE.md's socket guard did not exist | non-hermetic e2e; untested "no network" rule | autouse per-test DB + loopback-only socket guard |
| 9/29 mock fixtures did not match the API schema (one was a recorded 404 body) though `check_mocks.py` said "29/29 verified" | mock mode lied | `scripts/gen_mocks.py` records fixtures from a real demo; `check_mocks.py` validates against Pydantic models |
| UI pointed at nonexistent `cli replay`; sleeper page always said "TRIGGERED: HIGH"; FixLab applied fixes with no confirmation and a fake fallback policy id | misleading controls | fixed; Apply requires confirmation showing the measured price tag |

### Test results
| | Before | After |
|---|---|---|
| Backend tests | 107 passed | 121 passed |
| ruff check / format | 3 errors / 4 files | clean / clean |
| mypy | clean (82 files) | clean (86 files) |
| Frontend tests | 1 | 7 |
| Mock fixtures schema-valid | 20/29 (unchecked) | 29/29 (checked) |
| `cli demo` on fresh DB | crash | completes, ~25 s, exit 0 |

### Measured demo result (simulated target, `acme` suite)
Full policy: 7/7 attacks (5 critical, 2 high), 10/10 benign, sleeper `triggered`. Audit: granted 10,
needed 8 (derived from passing benign runs; equals the declared ground truth), excess `delete_file`,
`set_role`. After applying 4 zero-cost Pareto fixes and re-measuring: **0/7 attacks, 10/10 benign,
sleeper `trigger_blocked`** (poisoned memory still present — reported as residual risk).

### Benchmark (`uv run python scripts/benchmark.py 5`)
- Full-policy measurement (7 attacks incl. 3-session sleeper + 10 benign): median 0.50 s, max 0.54 s;
  5/5 identical outcome digests (deterministic). Machine: dev laptop, Windows 11, SQLite file DB.
- State-diff verdict vs an output-only keyword baseline (strawman defined in the script), 6 single-session cases:
  agent that attacks but replies innocently → state-diff 6/6, output-only 0/6;
  agent that only *says* it will attack → state-diff 0/6, output-only 6/6.
  Scope: one synthetic suite, deterministic agent — not a real-world detection rate.

### Remaining limitations / not done
- P2: trace explorer filtering by event type; frontend tests beyond route smoke tests.
- The GitHub Actions example was not executed on GitHub (its commands were run locally).
- No real-model (Ollama) run in this pass; `openai_compat` path untested here.
- Local `data/agentbreak.db` contains old test pollution from before tests were isolated
  (duplicate old-fingerprint findings). Left untouched; delete or move it for a clean dashboard.
- Mock fixtures carry real ids/timestamps; regenerating them changes many lines.
