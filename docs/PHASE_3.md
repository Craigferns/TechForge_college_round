# Phase 3: Simulated AI Agent — Contributor Guide

> **Phase Status:** Complete (M3.1 through M3.3 fully implemented, verified, and quality-gated).
> **Scope Boundary:** Phase 3 unifies simulated (scripted) and real (OpenAI-compatible) AI agents behind the `BaseTarget` contract, establishes the pure `run_once` execution loop, implements connectivity and tool-calling capability probing, and activates the targets, suites, and policies REST API layer with database seeding.

---

## 1. Overview of Phase 3 Milestones

| Milestone | Title | Focus Area | Status |
|---|---|---|---|
| **M3.1** | **Target Interface, `ScriptedAgent`, `run_once`** | `BaseTarget` abstract pipeline interface, `ScriptedAgent` conforming to AgentDojo `BasePipelineElement`, `ScriptedTarget`, pure `run_once` execution loop, 10/10 benign ground truth pass & determinism | **Complete** |
| **M3.2** | **OpenAI-Compatible Adapter & Provider Probe** | `OpenAICompatTarget` pipeline construction, dynamic `api_key_env` resolution (zero secret storage), `llm/provider.py` reachability & structured `tool_calls` probe (< 5 s timeout) | **Complete** |
| **M3.3** | **Targets, Suites & Policies API** | Real operational routes for `targets` (CRUD + probe test), `suites/acme`, `scenarios` (4), `attack-cases` (7), `policies` (CRUD + structural diff), `seed.py` + `agentbreak cli seed` | **Complete** |

---

## 2. Technical Architecture Delivered

### 2.1 The Unified Target Architecture (`agentbreak/targets/`)
- **`BaseTarget` Interface (`backend/agentbreak/targets/base.py`):**
  - Contract common to all agent implementations:
    - Metadata: `id: str`, `name: str`, `kind: str`, `config: dict[str, Any]`.
    - `build_pipeline(runtime: FunctionsRuntime, env: Any) -> BasePipelineElement`: Assembles an AgentDojo pipeline element.
    - `query(prompt, runtime, env, messages, extra_args)`: Standard execution wrapper.
  - Targets are cleanly decoupled from verdicts, attack security logic, and injection predicates.
- **Factory (`backend/agentbreak/targets/factory.py`):**
  - `create_target(target: Target) -> BaseTarget`: Dispatches target entities into concrete adapters (`scripted` or `openai_compat`).

---

### 2.2 Scripted Deterministic Agent (`agentbreak/targets/scripted.py`)
- **`AgentProfile`:**
  - `obeys: frozenset[str] | None`: Set of injection task IDs the agent is permitted to obey (default: `None`, obeying all injection markers).
  - `memory_bootstrap: bool`: When `True`, calls `read_memory()` on session start if granted.
  - `says_only: bool`: When `True`, writes exploit intention into final model output text without calling unauthorized tools (used for `said_not_did` classification testing).
- **Behavioral Loop:**
  1. **Bootstrap:** Calls `read_memory()` if granted. If the result contains `[[AB:IT-04T]]`, activates memory trigger.
  2. **Plan:** Matches the incoming query against `ALL_BENIGN_TASKS` and queues the task's `ground_truth(env)` tool calls.
  3. **Execution & Memory Trigger:** Pops calls one at a time. If the memory trigger is active and the call is `send_email`, appends attacker `mallory@evil.test` to `bcc`.
  4. **Injection Marker Scan:** After each tool execution, scans result text for markers matching `[[AB:<IT-id>]]`. If the ID is in `profile.obeys`, queues that injection task's ground-truth calls.
  5. **Denied Handling:** If an unauthorized tool or argument constraint is denied by `PolicyRuntime`, records the error message and continues without retry or improvisation.
  6. **Finish:** Returns ground-truth output or exploit intention.

---

### 2.3 Pure Execution Engine Loop (`agentbreak/engine/loop.py`)
- **`run_once` Pure Function:**
  - Signature: `run_once(target, policy, user_task, injection_task=None, injections=None, memory_in=None) -> RunOutcome`.
  - Zero disk I/O or DB side effects.
  - Clones environment into `pre` snapshot.
  - Wraps tools in `PolicyRuntime(policy)` enforcing grants and argument constraints before execution.
  - Queries target pipeline and captures `post` environment state.
  - Evaluates `utility = user_task.utility(...)` and `security = injection_task.security(...)`.
  - Returns immutable `RunOutcome(pre, post, messages, model_output, utility, security)`.

---

### 2.4 OpenAI-Compatible Adapter & Probe (`agentbreak/targets/openai_compat.py` & `agentbreak/llm/provider.py`)
- **`OpenAICompatTarget`:**
  - Assembles `AgentPipeline([SystemMessage(...), InitQuery(), OpenAILLM(...), ToolsExecutionLoop([ToolsExecutor(), OpenAILLM(...)])])`.
  - Dynamic API key resolution: reads `os.environ[config["api_key_env"]]` on demand so API tokens are never written to database tables or serialized to disk.
- **Provider Probing (`probe_target`):**
  - Two-stage validation under strict 5.0 s timeout:
    1. **Reachability:** Checks `GET /models` endpoint.
    2. **Tool-Calling Capability:** Sends a 1-tool probe request (`probe_tool(x='ping')`). Verifies that `choices[0].message.tool_calls` is populated. Rejects text-only or thinking-only models with clear diagnostic messages.

---

### 2.5 REST APIs & Database Seeding (`agentbreak/api/` & `agentbreak/seed.py`)
- **Active Endpoints:**
  - `GET /api/v1/targets`: Lists registered targets from SQLite.
  - `POST /api/v1/targets`: Registers a new target.
  - `GET /api/v1/targets/{id}`: Retrieves specific target.
  - `DELETE /api/v1/targets/{id}`: Deletes target (with 409 conflict guard if runs reference it).
  - `POST /api/v1/targets/{id}/test`: Tests target connectivity and tool calling.
  - `GET /api/v1/suites/acme`: Returns 10 tools with JSON schemas and effect classes, 10 benign tasks, 5 injection tasks, and vectors.
  - `GET /api/v1/scenarios`: Returns 4 core attack scenarios (`ipi-exfil`, `malicious-doc`, `sleeper-memory`, `priv-esc`).
  - `GET /api/v1/attack-cases`: Returns 7 attack cases (`AS-01` through `AS-07`).
  - `GET /api/v1/policies`: Lists security policies.
  - `POST /api/v1/policies`: Creates policy with SHA-256 canonical hashing.
  - `GET /api/v1/policies/{id}`: Retrieves policy.
  - `GET /api/v1/policies/{a}/diff/{b}`: Computes structural grant diff.
- **CLI Seeding:**
  - `uv run python -m agentbreak.cli seed`:
    - Idempotently creates default policies: `pol_full` (all 10 tools) and `pol_needed` (8 needed tools).
    - Seeds default target: `tgt_demo_scripted` ("Simulated Target (Scripted)").

---

## 3. Quality Gate Results & Verification

All quality gates pass with zero errors across both Python and TypeScript stacks:

```bash
# 1. Backend unit tests (55 passed in 4.70s, 0 failures)
uv run pytest -m "not ollama"

# 2. Python linter and formatter (0 errors, 72 files checked)
uv run ruff check .
uv run ruff format --check .

# 3. Static type checker (0 errors across 55 source files)
uv run mypy backend/agentbreak

# 4. Acme suite ground-truth check (10/10 benign ground truths passed)
uv run python -m agentbreak.cli check-suite acme

# 5. Database seeding command (idempotent, 0 errors)
uv run python -m agentbreak.cli seed

# 6. Synthetic data safety linter (.test domains & canary validation)
uv run python scripts/lint_fake_data.py

# 7. Frontend TypeScript, ESLint, Vitest, and Production build
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

---

## 4. Key Engineering Insights & Gotchas

1. **`PolicyRuntime` as `FunctionsRuntime` Subclass:**
   - In AgentDojo, the agent execution loop expects `runtime` to be an instance of `FunctionsRuntime` offering `run_function(env, function, kwargs)`.
   - `PolicyRuntime` inherits from `FunctionsRuntime` and overrides `run_function` with pre-execution policy enforcement. Only granted tools are present in `self.functions`, preventing ungranted schemas from ever reaching real LLM models.
2. **Pydantic Model Class vs. Instance Schemas:**
   - In AgentDojo's `Function` objects, `f.parameters` is the Pydantic `BaseModel` *class* (not an instance). Parameter JSON schemas must be retrieved via `f.parameters.model_json_schema()`.
3. **Secrets Isolation in Target Configurations:**
   - Real LLM API keys are never stored in the database. The `config` stores `api_key_env` pointing to the environment variable name (e.g. `OPENAI_API_KEY`), which `OpenAICompatTarget.resolve_api_key()` dynamically retrieves at runtime.
4. **Tool-Calling Model Requirement:**
   - Models that do not emit OpenAI-formatted `tool_calls` (e.g. pure conversational or reasoning models that only output Markdown) are explicitly flagged by `probe_target` with clear guidance.
