-- AgentBreak Database Schema
-- SQLite with WAL mode, foreign keys enabled, and busy timeout

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

-- Immutable security policies
CREATE TABLE IF NOT EXISTS policy (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  parent_id TEXT REFERENCES policy(id),
  grants_json TEXT NOT NULL,
  hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

-- Agent targets under evaluation
CREATE TABLE IF NOT EXISTS target (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL CHECK (kind IN ('scripted', 'openai_compat')),
  config_json TEXT NOT NULL,
  active_policy_id TEXT REFERENCES policy(id),
  created_at TEXT NOT NULL
);

-- Individual evaluation and replay runs
CREATE TABLE IF NOT EXISTS run (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('attack', 'benign', 'control')),
  target_id TEXT NOT NULL REFERENCES target(id),
  policy_id TEXT NOT NULL REFERENCES policy(id),
  suite TEXT NOT NULL,
  case_id TEXT,
  scenario_id TEXT,
  user_task_id TEXT NOT NULL,
  injection_task_id TEXT,
  template_id TEXT,
  payload_text TEXT,
  payload_hash TEXT,
  mutation_chain_json TEXT,
  origin TEXT CHECK (origin IN ('static', 'mutated', 'llm')),
  trial_idx INTEGER NOT NULL DEFAULT 0,
  seed INTEGER,
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'error', 'cancelled')),
  error TEXT,
  utility INTEGER,
  security INTEGER,
  model_output TEXT,
  repro_json TEXT NOT NULL,
  sleeper_session_id TEXT,
  discovery_campaign_id TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_run_lookup ON run(target_id, policy_id, created_at);

-- Tool invocation traces (cascades on run deletion)
CREATE TABLE IF NOT EXISTS trace_step (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES run(id) ON DELETE CASCADE,
  idx INTEGER NOT NULL,
  role TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('system', 'user', 'assistant', 'tool_call', 'tool_result')),
  tool TEXT,
  args_json TEXT,
  content TEXT,
  flags_json TEXT NOT NULL DEFAULT '{}',
  caused_by_idx INTEGER,
  UNIQUE (run_id, idx)
);

-- Pre- and post-environment snapshots (cascades on run deletion)
CREATE TABLE IF NOT EXISTS env_snapshot (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES run(id) ON DELETE CASCADE,
  phase TEXT NOT NULL CHECK (phase IN ('pre', 'post')),
  env_json TEXT NOT NULL,
  UNIQUE (run_id, phase)
);

-- Deterministic verdict per run
CREATE TABLE IF NOT EXISTS verdict (
  run_id TEXT PRIMARY KEY REFERENCES run(id) ON DELETE CASCADE,
  success INTEGER NOT NULL,
  classification TEXT NOT NULL CHECK (classification IN ('exploited', 'blocked', 'said_not_did', 'invalid_run', 'error')),
  impact_class TEXT,
  severity TEXT CHECK (severity IN ('critical', 'high', 'medium', 'low', 'none')),
  evidence_json TEXT NOT NULL,
  verifier_version TEXT NOT NULL,
  verdict_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Deduplicated vulnerability findings
CREATE TABLE IF NOT EXISTS finding (
  id TEXT PRIMARY KEY,
  fingerprint TEXT NOT NULL UNIQUE,
  target_id TEXT NOT NULL REFERENCES target(id),
  scenario_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  title TEXT NOT NULL,
  severity TEXT NOT NULL,
  impact_class TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open', 'fixed', 'regressed', 'accepted_risk', 'partially_mitigated')),
  success_rate REAL NOT NULL DEFAULT 1.0,
  confidence TEXT NOT NULL DEFAULT 'confirmed',
  enabling_permissions_json TEXT NOT NULL DEFAULT '[]',
  first_run_id TEXT REFERENCES run(id),
  last_run_id TEXT REFERENCES run(id),
  occurrences INTEGER NOT NULL DEFAULT 1,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_finding_status ON finding(status, severity);

CREATE TABLE IF NOT EXISTS finding_run (
  finding_id TEXT NOT NULL REFERENCES finding(id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES run(id) ON DELETE CASCADE,
  PRIMARY KEY (finding_id, run_id)
);

-- Sleeper runs and sessions
CREATE TABLE IF NOT EXISTS sleeper_run (
  id TEXT PRIMARY KEY,
  target_id TEXT NOT NULL REFERENCES target(id),
  policy_id TEXT NOT NULL REFERENCES policy(id),
  case_id TEXT NOT NULL,
  gap_sessions INTEGER NOT NULL DEFAULT 1,
  seed INTEGER,
  status TEXT NOT NULL,
  outcome TEXT CHECK (outcome IN ('plant_failed', 'trigger_blocked', 'triggered')),
  created_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS sleeper_session (
  id TEXT PRIMARY KEY,
  sleeper_run_id TEXT NOT NULL REFERENCES sleeper_run(id) ON DELETE CASCADE,
  idx INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('plant', 'gap', 'trigger')),
  run_id TEXT REFERENCES run(id),
  memory_before_json TEXT,
  memory_after_json TEXT,
  UNIQUE (sleeper_run_id, idx)
);

-- Autonomous discovery campaigns
CREATE TABLE IF NOT EXISTS discovery_campaign (
  id TEXT PRIMARY KEY,
  target_id TEXT NOT NULL REFERENCES target(id),
  policy_id TEXT NOT NULL REFERENCES policy(id),
  scenario_ids_json TEXT NOT NULL,
  budget_json TEXT NOT NULL,
  seed INTEGER NOT NULL,
  use_attacker_llm INTEGER NOT NULL,
  status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  successes INTEGER NOT NULL DEFAULT 0,
  coverage_json TEXT,
  created_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS discovery_attempt (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id TEXT NOT NULL REFERENCES discovery_campaign(id) ON DELETE CASCADE,
  n INTEGER NOT NULL,
  case_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  origin TEXT NOT NULL,
  mutation_chain_json TEXT,
  run_id TEXT REFERENCES run(id),
  success INTEGER,
  UNIQUE (campaign_id, fingerprint)
);

-- Permission audits
CREATE TABLE IF NOT EXISTS permission_audit (
  id TEXT PRIMARY KEY,
  target_id TEXT NOT NULL REFERENCES target(id),
  policy_id TEXT NOT NULL REFERENCES policy(id),
  status TEXT NOT NULL,
  stage TEXT,
  granted_json TEXT,
  needed_json TEXT,
  excess_json TEXT,
  rows_json TEXT,
  minimal_policy_id TEXT REFERENCES policy(id),
  proof_json TEXT,
  created_at TEXT NOT NULL,
  finished_at TEXT
);

-- Candidate fix evaluations with price tags
CREATE TABLE IF NOT EXISTS fix_eval (
  id TEXT PRIMARY KEY,
  audit_id TEXT REFERENCES permission_audit(id),
  target_id TEXT NOT NULL REFERENCES target(id),
  base_policy_id TEXT NOT NULL REFERENCES policy(id),
  fix_json TEXT NOT NULL,
  result_policy_id TEXT REFERENCES policy(id),
  trials INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL,
  attacks_total INTEGER,
  attacks_blocked INTEGER,
  benign_total INTEGER,
  benign_broken INTEGER,
  pareto INTEGER,
  details_json TEXT,
  retest_of TEXT REFERENCES fix_eval(id),
  created_at TEXT NOT NULL,
  finished_at TEXT
);

-- Evidence reports
CREATE TABLE IF NOT EXISTS report (
  id TEXT PRIMARY KEY,
  scope_json TEXT NOT NULL,
  format TEXT NOT NULL DEFAULT 'markdown',
  markdown TEXT NOT NULL,
  meta_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
