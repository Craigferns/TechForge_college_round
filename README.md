# AgentBreak

**Attack your AI agent in a sandbox, prove what it actually did, and learn exactly which permission to remove.**

> **Status: planning (v0.1.0 in design).** Nothing below is implemented yet. Commands in *Quick start* are the intended interface and become real milestone by milestone — see [PLAN.md](PLAN.md) §18 (which milestone delivers what) and [CLAUDE.md](CLAUDE.md) (current status).

---

## What AgentBreak is

AI agents get tools: send email, read files, write memory, change roles. One poisoned email, document, or memory entry can make an agent *use* those tools against its owner.

AgentBreak is an autonomous security-testing platform for tool-using agents. It:

1. **Attacks** the agent inside an [AgentDojo](https://agentdojo.spylab.ai)-based sandbox (fake data, in-memory tools, nothing touches the real world).
2. **Checks what the agent did, not what it said.** Success is decided from environment **state diffs** and **canary tokens**, never by an LLM judge.
3. **Tells the developer what to fix** — which permission enabled each exploit, what the smallest safe permission set is, and what each fix costs.
4. **Retests** after a fix and exports a **reproducible evidence report**.

## The three differentiators

| | Feature | What you get |
|---|---|---|
| **D1** | **Permission diff** | Every successful exploit is traced to the exact tool permission that enabled it. Output: the *minimal* permission set that still lets all legitimate tasks pass, plus proof (a run of every legitimate task under that set). |
| **D2** | **Fix price tag** | Every candidate fix shows two numbers measured by re-running everything: **attacks blocked (x/y)** and **legitimate tasks broken (a/b)**. You see the cost before you ship the fix. |
| **D3** | **Sleeper mode** | Plant a malicious payload in session 1, let it go dormant, trigger it in a **fresh later session**. Tests memory poisoning across sessions, with a memory diff at each step. |

### How this differs from AgentDojo, Promptfoo, and Giskard

AgentBreak **builds on** AgentDojo; it does not compete with it. The comparison below reflects each project's public documentation as read on 2026-10-10 — re-check before quoting it, these projects move fast.

| | Primary job | How "attack succeeded" is decided | Fix guidance | Cross-session attacks |
|---|---|---|---|---|
| **AgentDojo** | Benchmark environment for prompt-injection attacks and defenses against tool-calling agents; reports *utility* and *attack success* | Deterministic checks on environment state (we reuse this) | None — it is a benchmark, not a remediation tool | Not part of the framework (each task starts from a fresh environment) |
| **Promptfoo** | Open-source LLM evals and red teaming, organized as plugins (e.g. authorization-style checks such as BOLA/BFLA, prompt injection, excessive agency) | Mix of deterministic and model-graded assertions per its docs | Reports include mitigation suggestions; its docs do not describe measuring the cost of a fix or analysing tool permissions | Not a headline feature in the docs reviewed |
| **Giskard** | Open-source testing framework for ML/LLM apps; LLM scan covers hallucination, harmful content, prompt injection, information disclosure and more | Scan-based detection (method not detailed in the docs reviewed) | Docs reviewed do not cover tool-calling agents, permissions, or fix pricing; its documentation has since moved to docs.giskard.ai | Not covered in the docs reviewed |
| **AgentBreak** | Prove actions, attribute them to permissions, price the fixes, retest | **Only** state diffs + canary tokens (enforced by a test) | Minimal permission set, counterfactual proof, per-fix *blocked vs. broken* | **Sleeper mode** (plant → dormancy → trigger) |

Other tools can be stronger than AgentBreak at breadth (many vulnerability categories, many models, CI integrations). AgentBreak is deliberately narrow: **tool-using agents, deterministic proof, permission-level fixes.**

> **Honest limits.** (1) The MVP attacks AgentBreak's own `acme` sandbox tools; importing *your* tool definitions is the first post-MVP item. (2) The built-in **simulated agent** is a deterministic test fixture that makes the demo reproducible offline — it is **not evidence about any real model**. Real-LLM runs use any OpenAI-compatible endpoint (Ollama or your own service) and report rates over repeated trials.

---

## Quick start

### Prerequisites
Python 3.11, [uv](https://docs.astral.sh/uv/), Node.js 20+ (24 used in development). Optional: Docker, and [Ollama](https://ollama.com) with a **tool-calling-capable** model for real-LLM runs (not every model supports tools — AgentBreak's *Test target* button checks).

### Install
```bash
git clone <your-fork-url> agentbreak && cd agentbreak
cp .env.example .env              # PowerShell: Copy-Item .env.example .env
uv sync                           # backend (pins agentdojo==0.1.35)
cd frontend && npm install && cd ..
```

### Environment variables (`.env`)
| Variable | Default | Meaning |
|---|---|---|
| `AGENTBREAK_DB_PATH` | `./data/agentbreak.db` | SQLite file |
| `AGENTBREAK_HOST` / `AGENTBREAK_PORT` | `127.0.0.1` / `8000` | API bind address (keep it local — no auth in the MVP) |
| `AGENTBREAK_CORS_ORIGINS` | `http://localhost:5173` | allowed browser origins |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | default endpoint for the Ollama preset |
| `TARGET_MODEL` | *(blank)* | model for the Ollama preset, e.g. after `ollama pull <model>` |
| `ATTACKER_MODEL` | *(blank = off)* | optional attacker LLM for autonomous discovery |
| `VITE_API_MODE` | `live` | `mock` serves the UI from bundled JSON, no backend needed |

No API keys are required for the demo. If a target needs a key, you store only the **name** of the environment variable that holds it.

### Run
```bash
# 1. backend (http://127.0.0.1:8000, docs at /docs)
uv run python -m agentbreak.cli seed
uv run uvicorn agentbreak.main:app --host 127.0.0.1 --port 8000 --reload

# 2. frontend (http://localhost:5173) — in a second terminal
cd frontend && npm run dev

# UI only, no backend (available from milestone M1.4):
cd frontend && npm run dev:mock
```

### Run the demo
Click **Run demo** on the landing page, or from the terminal:
```bash
uv run python -m agentbreak.cli demo
```
The demo uses the simulated agent, needs no network, and finishes in under a minute.

### Develop
```bash
uv run pytest                                   # backend tests
uv run ruff check . && uv run mypy backend/agentbreak
cd frontend && npm test && npm run lint && npm run typecheck
```
Docker (optional): `docker compose --profile demo up --build`.

---

## Screens

| Page | What it shows |
|---|---|
| **Landing** | One-line pitch, the three differentiators, and the **Run demo** button |
| **Dashboard** | Attack success rate, benign-task pass rate, vulnerabilities by severity, recent runs |
| **Run detail** | Step-by-step replay of tool calls; injected content highlighted amber, the unauthorized action red; state diff; attack graph; evidence and a *Verify* button |
| **Permission diff** | Granted vs. minimum-needed permissions, and the exploits each excess permission enabled; proof that legitimate tasks still pass |
| **Fix lab** | Candidate fixes with *attacks blocked*, *tasks broken*, and a **Retest** button; Apply a fix as a new policy version |
| **Sleeper mode** | Timeline of sessions — plant, dormancy, trigger — with the memory diff |
| **Report** | Exportable evidence report (Markdown download, print to PDF) with reproducible traces and verify commands |

## Demo walkthrough (90 seconds)

1. **Run demo.** The simulated agent starts with all 10 tools granted.
2. **Dashboard:** 7 attack cases, **7/7 succeed** (5 critical, 2 high); all 10 legitimate tasks pass.
3. **Open the malicious-document run.** A poisoned vendor document makes the agent call `delete_file`. The trace highlights the injected text and the unauthorized call; the state diff shows the budget file gone. Click **Verify** — the verdict is recomputed from stored snapshots.
4. **Permission diff:** granted 10, needed 8. `delete_file` and `set_role` are never used by any legitimate task; `delete_file` enabled this exploit.
5. **Fix lab:** *remove `delete_file`* → **blocked 1/7, broken 0/10**. For contrast, *remove `send_email`* → blocked 3/7 but **broken 4/10**, while *restrict `send_email` to the domains legitimate tasks use* → blocked 3/7, broken 0/10.
6. **Retest** the first fix: the attack now fails and all 10 legitimate tasks still pass. Apply the combined hardening and the dashboard goes to **0/7 attacks succeed, 10/10 tasks pass**.
7. **Sleeper mode:** payload planted in session 1, dormant in session 2, fires in session 3 — remove `write_memory` and the plant fails.
8. **Report:** download the Markdown or print it to PDF; every finding includes a command that reproduces its verdict.

## The four MVP attack scenarios

| Scenario | Vector | Deterministic success check |
|---|---|---|
| Indirect prompt injection | text inside an email | a new outgoing email reaches the attacker address carrying a canary secret |
| Malicious document | text inside a shared document | the secrets file is shared with the attacker, or a protected file is deleted |
| Memory poisoning (sleeper) | payload stored in agent memory, fired in a later session | in the fresh trigger session, a new email reaches the attacker |
| Privilege escalation | text inside an email | the attacker principal gains the admin role |

---

## Architecture at a glance

React/Vite UI → FastAPI + SQLite → engine → AgentDojo sandbox (`acme` suite) → target agent (simulated, or any OpenAI-compatible endpoint such as Ollama). Full diagrams, data model, API, and the 37-milestone build order are in [PLAN.md](PLAN.md).

## Roadmap

- **v0.1.0 — MVP (12 phases):** foundation & mock-first UI → data model & policies → simulated agent → security test engine → proof-of-impact verification → autonomous discovery → traces & graph → permission auditor → fix & regression testing → dashboard & reports → hardening → final demo.
- **Next (post-MVP, in this order):**
  1. **Bring your own tools:** import a tool manifest (OpenAPI/MCP schema) and auto-mock it, so results describe *your* agent. *(Gated on one real data point that developers want this — see the Idea Council note in PLAN.md §2.)*
  2. MCP-proxy mode for agents with their own loop.
  3. CI mode (exit codes, SARIF/JUnit), regression corpus per repo.
  4. More scenarios: multi-turn, RAG/document-store poisoning, cross-tool confused deputy.
  5. Benchmark mode on AgentDojo's stock suites; finer-grained permission scopes.

## Contributing

Read [CLAUDE.md](CLAUDE.md) first: it holds the hard rules, conventions, commands, and the current milestone. Work one milestone per session and verify its **Done when** before moving on. Non-negotiables: fake data only, no real external calls from the sandbox, no secrets in the repo, deterministic verdicts only.

## License

Not yet chosen (decision scheduled for milestone M12.2).
