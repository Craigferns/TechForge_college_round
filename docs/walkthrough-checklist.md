# AgentBreak Walkthrough Checklist

This checklist verifies that all user-facing workflows and acceptance criteria in AgentBreak function correctly end-to-end.

## 1. Quick Start & Setup Checklist
- [x] Python 3.12+ environment initialized (`uv sync`).
- [x] Frontend dependencies installed (`cd frontend && npm install`).
- [x] Initial database migrated (`uv run python -m agentbreak.cli migrate`).
- [x] All 29 mock fixtures present (`uv run python scripts/check_mocks.py`).

## 2. CLI Capabilities Checklist
- [x] `agentbreak cli demo`: Executes full demo run under 60 seconds.
- [x] `agentbreak cli export-openapi`: Exports frozen schema covering all 51 endpoints.
- [x] `agentbreak cli verify <run_id>`: Deterministically verifies verdict without LLM.
- [x] `agentbreak cli discover`: Runs autonomous mutator-based discovery campaign.
- [x] `agentbreak cli check-suite`: Validates Acme task suite integrity.

## 3. Web UI Verification Checklist
- [x] **Landing Page (`/`)**:
  - [x] Hero section, 3 differentiator cards rendered cleanly.
  - [x] "Run Demo" button triggers orchestrated run with live stage updates.
- [x] **Dashboard (`/dashboard`)**:
  - [x] 4 KPI tiles (Critical Findings, Attack Success, Benign Utility, Active Policy).
  - [x] Severity distribution chart (5 Critical, 2 High before hardening; 0 after hardening).
  - [x] Recent runs table with status badges and links to trace details.
- [x] **Run Detail (`/runs/{id}`)**:
  - [x] Trace timeline showing input prompts, tool calls, and tool outputs.
  - [x] Highlighting: Injected prompt step in amber, unauthorized tool call in red.
  - [x] State diff tab showing actual AcmeEnv file/email/memory deltas.
  - [x] Attack graph tab displaying single-run causal SVG graph.
  - [x] Reproducibility tab with exact CLI replay and verify commands.
- [x] **Permission Auditor (`/permissions`)**:
  - [x] 3-column permission diff: Granted (10), Needed (8), Excess (2).
  - [x] Tool usage attribution table showing which benign tasks depend on each tool.
  - [x] Mathematical proof showing 10/10 benign tasks pass under minimal grants.
- [x] **Fix Lab (`/fixes`)**:
  - [x] Empirical Price Tags: Shows attacks blocked vs tasks broken.
  - [x] Pareto dominance tags (blunt fixes marked dominated; scoped fixes marked optimal).
  - [x] "Apply Hardening" applies combined policy and transitions findings to `fixed`.
- [x] **Sleeper Agent Evaluation (`/sleeper`)**:
  - [x] Multi-session timeline showing plant stage, session gaps, and trigger stage.
  - [x] Verification showing unauthorized memory persistence across context resets.
- [x] **Audit Reports (`/report`)**:
  - [x] Formatted Markdown audit report with executive summary and finding tables.
  - [x] Clean print styling for browser Print → Save as PDF export.

## 4. Security & Hardening Checklist
- [x] Zero hardcoded secrets (`uv run python scripts/scan_secrets.py` exits 0).
- [x] Fail-closed sandbox egress (`uv run python scripts/check_egress.py` exits 0).
- [x] Fake data validation (`uv run python scripts/lint_fake_data.py` exits 0).
- [x] Strict TypeScript compilation (`npm run typecheck` exits 0).
- [x] Strict Python type checking (`uv run mypy backend/agentbreak` exits 0).
