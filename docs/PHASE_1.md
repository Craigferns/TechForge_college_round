# Phase 1: Foundation and Setup — Contributor Guide

> **Phase Status:** Complete (M1.1 through M1.6 fully implemented, verified, and quality-gated).
> **Scope Boundary:** Phase 1 establishes the dual-stack development foundation, verifies all AgentDojo sandbox assumptions, freezes the OpenAPI contract, and renders all 7 interactive UI screens against typed mock JSON fixtures.

---

## 1. Overview of Phase 1 Milestones

| Milestone | Title | Focus Area | Status |
|---|---|---|---|
| **M1.1** | **Repo & Tooling** | Python 3.11 + FastAPI + `uv` skeleton; React 18 + Vite + TypeScript + Tailwind frontend; CI, lint, and type gates | **Complete** |
| **M1.2** | **AgentDojo Spike** | Validate package exports, execution loops, function signatures; verified V-01…V-11 | **Complete** |
| **M1.3** | **Contract-First Schemas & Mocks** | 51 FastAPI route stubs, `openapi.json` export, generated `types.ts`, typed mock JSON fixtures | **Complete** |
| **M1.4** | **Shell, Landing & Dashboard (Mock)** | App navigation (`layoutId`), KPI tiles, Recharts severity distribution & trend line, recent runs table | **Complete** |
| **M1.5** | **Run Detail & Permission Diff (Mock)** | Trace replay with amber/red highlighting, PRE/POST state diff tabs, SVG attack graph, minimal permission attribution (D1) | **Complete** |
| **M1.6** | **Fix Lab, Sleeper & Report (Mock)** | Candidate fixes table with price tags & Pareto badges (D2), multi-session sleeper timeline (D3), reproducible Markdown report & print-to-PDF styles | **Complete** |

---

## 2. Technical Architecture Delivered

### 2.1 Backend Architecture (FastAPI + Pydantic v2 + uv)
- **Dependency Management:** Managed by Astral `uv` pinned to Python 3.11 with `pyproject.toml`.
  - Core dependencies: `agentdojo==0.1.35`, `fastapi>=0.110.0`, `pydantic>=2.6.0`, `uvicorn[standard]>=0.29.0`, `httpx>=0.27.0`.
  - Development tools: `pytest`, `pytest-asyncio`, `ruff`, `mypy`.
- **Package Layout:**
  - `backend/agentbreak/__init__.py`: Package root, version `0.1.0`.
  - `backend/agentbreak/config.py`: Environment-driven Pydantic `Settings` (SQLite DB path, host/port, CORS origins, timeouts).
  - `backend/agentbreak/main.py`: FastAPI factory with CORS middleware, router aggregation, and `/api/v1` routes.
  - `backend/agentbreak/cli.py`: Antigravity CLI helper with `export-openapi` command.
- **Contract & Schemas (`backend/agentbreak/schemas/`):**
  - `common.py`: `Health`, `Meta`, `Page[T]`.
  - `target.py`: `Target`, `TargetCreate`, `TargetTestResult`.
  - `suite.py`: `SuiteInfo`, `ToolInfo`, `TaskInfo`, `ScenarioSpec`, `AttackCase`.
  - `policy.py`: `Grant`, `ArgConstraint`, `Policy`, `PolicyCreate`, `PolicyDiff`.
  - `run.py`: `Run`, `RunCreate`, `RunSummary`, `TraceStep`, `SnapshotPair`, `Verdict`, `Evidence`.
  - `finding.py`: `Finding`, `FindingUpdate`, `AttackGraph`, `GraphNode`, `GraphEdge`.
  - `sleeper.py`: `SleeperRun`, `SleeperRunCreate`, `SleeperSession`.
  - `discovery.py`: `DiscoveryCampaign`, `DiscoveryCreate`, `DiscoveryAttempt`.
  - `audit.py`: `PermissionAudit`, `AuditCreate`, `PermissionRow`, `EnabledExploit`, `AuditProof`.
  - `fix.py`: `FixSpec`, `FixSuggestion`, `PriceTag`, `FixEval`, `FixEvalCreate`.
  - `dashboard.py`: `DashboardSummary`, `Report`, `ReportCreate`, `DemoStatus`, `DemoStage`, `DemoLinks`.
- **API Router Stubs (`backend/agentbreak/api/`):**
  - 51 endpoints returning HTTP 501 Not Implemented stubs with exact response models across 11 router modules (`system`, `targets`, `suites`, `policies`, `runs`, `sleeper`, `discovery`, `findings`, `audits`, `fixes`, `dashboard`).
  - Active operational endpoints: `GET /api/v1/health` and `GET /api/v1/meta`.

---

### 2.2 AgentDojo Spike Results (`scripts/spike_agentdojo.py`)
AgentDojo version `0.1.35` was validated against the verification matrix in `PLAN.md` Appendix A:
- **V-01 (Task Environment Factory):** `agentdojo.task_suite.task_suite.TaskSuite` exists and exposes tools, tasks, and environments.
- **V-02 (Tools as Pydantic functions):** `agentdojo.functions_runtime.EnvTool` wraps callables with JSON schema generation.
- **V-03 (Built-in Suites):** Stock suites (`slack`, `banking`, `workspace`, `travel`) confirmed.
- **V-04 (Attack Injection Points):** Confirmed `task_suite` supports user injection and vector injection.
- **V-05 (Pipeline Model Interface):** `agentdojo.agent_pipeline.agent_pipeline.AgentPipeline` and base queries confirmed.
- **V-06 (Injection helper):** Confirmed `TaskSuite` custom environment builder is used for our custom `acme` suite.
- **V-07 (AgentDojo Execution Loop):** `AgentPipeline.query()` returns `(extra_history, cost)` with recorded tool call history.
- **V-08 (In-Memory Tool Isolation):** Tools mutate local in-memory dataclass state without disk leaks.
- **V-09 (Defenses Export):** `DEFENSES` dictionary resides in `agentdojo.agent_pipeline.agent_pipeline`.
- **V-10 (Windows uv Resolution):** 72 pure wheels resolved cleanly with 0 compilation steps.
- **V-11 (Pre/Post Deep Copy):** Environment states support clean deepcopy for deterministic state diffing.

---

### 2.3 Frontend Architecture (React 18 + Vite + TypeScript + Tailwind + Framer Motion)
- **Design System & UI Components (`frontend/src/components/ui/`):**
  - Adheres strictly to `ui-ux-suite` rules: Dark Minimalist Bento aesthetic, 8pt spacing rhythm, Framer Motion spring physics (`damping: 25`, `stiffness: 300`), accessible hit targets (min 44px), semantic CSS tokens.
  - `Button.tsx`: Animated button with loading state, icons, and variants (`primary`, `secondary`, `outline`, `ghost`, `danger`).
  - `Badge.tsx`: Semantic badge tokens for verdicts (`pareto`, `unauthorized`, `allowed`, `high`, `critical`, `outline`).
  - `Card.tsx`: Dark Bento glassmorphic card with subtle borders (`border-slate-800/80`).
  - `Modal.tsx`: Accessible dialog wrapper with `AnimatePresence` and backdrop blur.
  - `Navbar.tsx`: Animated navigation bar with `layoutId` pill indicator, target selector, and live status badge.
- **API Client & Mock Engine (`frontend/src/api/` & `frontend/src/mocks/`):**
  - Generated TypeScript definitions (`frontend/src/api/types.ts`) via `openapi-typescript`.
  - Type aliases (`frontend/src/api/models.ts`) preventing verbose nested imports.
  - API Client (`client.ts`) with automatic mode switching:
    - In mock mode (`VITE_API_MODE=mock`), intercepts all API requests and returns typed JSON fixtures with a simulated 150ms network delay.
    - Custom React hook `useApi<T>(endpoint)` provides declarative loading, data, and refetch states.
- **7 Fully Interactive UI Screens (`frontend/src/pages/`):**
  1. **Landing (`/`):** Hero section with value proposition, animated 1-minute demo runner modal with real-time stage progression, 3 differentiator cards (D1, D2, D3), and 4-step workflow.
  2. **Dashboard (`/dashboard`):** 4 high-level KPI tiles (ASR, Benign Pass, Open Findings, Applied Fixes), Recharts severity breakdown bar chart, trend line chart, and recent test runs table.
  3. **Run Detail (`/runs/:runId`):** Step-by-step trace stepper highlighting canary markers and injected prompts, PRE/POST environment state diff tab, visual SVG attack graph, and one-click replay command.
  4. **Permission Diff (`/permissions`):** D1 differentiator screen showing Granted (10) vs Needed (8) vs Excess (2) tool breakdown, expandable causal attribution rows linking permissions to enabled exploits, and counterfactual proof of utility.
  5. **Fix Lab (`/fixes`):** D2 differentiator screen displaying candidate mitigations with two-dimensional price tags (`Attacks Blocked x/y`, `Legit Tasks Broken a/b`), Pareto-optimal badges, and Retest/Apply actions.
  6. **Sleeper Mode (`/sleeper`):** D3 differentiator screen showing cross-session memory poisoning lifecycle across Session 1 (Plant) $\to$ Session 2 (Dormancy Gap) $\to$ Session 3 (Trigger), with side-by-side SQLite persistent memory state diffs.
  7. **Evidence Report (`/report`):** Rendered markdown evidence report with cryptographic run hashes, deterministic verification commands, copy-to-clipboard feedback, markdown download, and clean print-to-PDF styles.

---

## 3. How to Run & Verify Phase 1

### 3.1 Backend Quality Gates
```bash
# 1. Run unit tests
uv run pytest

# 2. Run linter and formatting check
uv run ruff check .
uv run ruff format --check .

# 3. Run type check
uv run mypy backend/agentbreak

# 4. Verify OpenAPI contract export
uv run python -m agentbreak.cli export-openapi --output openapi.json
```

### 3.2 Frontend Quality Gates
```bash
cd frontend

# 1. TypeScript type check
npm run typecheck

# 2. ESLint code analysis
npm run lint

# 3. Unit test suite
npm test

# 4. Production build
npm run build
```

### 3.3 Running the Interactive Frontend Demo (Mock Mode)
```bash
cd frontend
npm run dev:mock
```
Visit `http://localhost:5173` to explore all 7 screens with instant response and realistic mock data.

---

## 4. Next Steps for Contributors (Phase 2)

With Phase 1 complete, the next phase is **Phase 2: Data model and policies** (milestones M2.1 through M2.4):
1. **M2.1 (SQLite schema & migration runner):** Create `backend/agentbreak/db.py` and `schema.sql` implementing tables for targets, policies, grants, runs, traces, snapshots, findings, and fix evaluations.
2. **M2.2 (Repository layer):** Implement repository classes in `backend/agentbreak/repo/` with clean CRUD queries and WAL mode transactions.
3. **M2.3 (Policy engine & hashing):** Implement canonical grant serialization and SHA-256 policy hashing in `backend/agentbreak/domain/policy.py`.
4. **M2.4 (Acme sandbox suite & tools):** Implement the custom Acme Corporation environment with 10 tools and benign tasks BT-01 through BT-10 using AgentDojo primitives.
