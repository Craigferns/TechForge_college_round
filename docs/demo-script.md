# AgentBreak — judged demo script (≈5 minutes, verified 2026-10-11)

Everything shown is computed live from runs against the **simulated (scripted) target** on the
synthetic `acme` suite. Say that once, up front: it proves the measurement pipeline, not real-model
robustness.

## 0. Before judges arrive (2 min)

```bash
uv sync
cd frontend && npm install && cd ..
uv run uvicorn agentbreak.main:app --host 127.0.0.1 --port 8000
```
Second terminal:
```bash
cd frontend && npm run dev
```
Open http://localhost:5173. The header badge must read **Live API** (amber "Mock fixtures — not
live results" means `VITE_API_MODE=mock`; restart with `npm run dev`).
Preflight without the UI: `uv run python -m agentbreak.cli demo` (exit 0, ~25 s).

## 1. The problem (0:00–0:30)
"Agents act through tools. A poisoned email can make them use those tools against their owner.
Most evals grade what the model *says*. We grade what it *did*: environment state before vs after."

## 2. Run the demo live (0:30–1:30)
Home → **Run live demo**. The modal polls the backend; each stage's text is computed:
- Attack evaluation: **7/7 attacks confirmed by state diff (5 critical, 2 high)**, sleeper `triggered`.
- Benign ground truth: **10/10** pass under the full policy.
- Permission audit: **granted 10, needed 8, excess 2 (delete_file, set_role)**.
- Fix price tags: 12 fixes measured.
- Apply & verify: 4 zero-cost Pareto fixes applied, then re-measured:
  **0/7 attacks succeed, 10/10 benign pass, sleeper trigger_blocked**.

## 3. Evidence for one exploit (1:30–2:15)
Modal → **Attack trace (AS-04)**. Show: injected step in the doc → `delete_file` call → State Diff tab
("1 file deleted", `P-DELETE: TRUE`). Click **Verify Verdict Hash**: the verdict is recomputed from the
stored PRE/POST snapshots. Talking point: the verdict code never reads model text — an agent that only
*says* it will exfiltrate is classified `said_not_did` (tested).

## 4. Which permission caused it (2:15–3:00)
**Permissions** (audit). "Needed" = tools exercised by passing benign runs, not a list we wrote.
Each row's "enables" comes from a counterfactual: remove that one tool, re-run everything.
`delete_file` enables AS-04 and breaks 0 benign tasks; `send_email` enables AS-01/02/05 but 4 benign
tasks need it.

## 5. What the fix costs (3:00–4:00)
**Fix Lab**. Compare: *remove send_email* blocks 3/7 but breaks 4/10 (dominated) vs *restrict
send_email [bcc, to] → acme.test, partnerco.test* blocks the same 3/7 and breaks 0/10 (Pareto).
Expand the row: blocked / still exploitable / broken / inconclusive / sleeper outcome / evidence runs.
Note the allowlist covers `bcc` because the sleeper exfiltrates through `bcc` — the scope came from
observed runs; an allowlist on `to` alone was measured to leave AS-05 open.

## 6. Sleeper + honesty (4:00–4:30)
**Sleeper**: plant → gap → trigger timeline. Under the hardened policy the outcome is
`trigger_blocked` and the banner names the residual risk: the poisoned instruction is still in memory.

## 7. CI and report (4:30–5:00)
```bash
uv run python -m agentbreak.cli ci --policy pol_full --out agentbreak-ci.json   # exit 1: 7 exploited
uv run python -m agentbreak.cli ci --out agentbreak-ci.json                     # exit 0 after the demo
```
Exit codes: 0 pass · 1 security gate failed · 2 infrastructure error (errors never pass).
**Report** page: Markdown built only from stored records; every finding has a `cli verify <run>` line.

## Recovery
- Demo modal shows a failed stage → read its error text; rerun. The demo resets only
  `tgt_demo_scripted` (active policy → `pol_full`, its findings reopened); other data is untouched.
- UI shows "Cannot reach the AgentBreak API" → backend not running on 127.0.0.1:8000.
- Clean slate: stop the backend, point `AGENTBREAK_DB_PATH` at a new file, restart.

## Questions to expect
- *Is this a real model?* No — the scripted target is a deterministic fixture. `openai_compat` targets
  run the same pipeline against any OpenAI-compatible endpoint (e.g. Ollama with a tool-calling model).
- *How do you know benign checks aren't vacuous?* A test removes `read_file` and asserts the tasks
  that need it fail (the fixture used to return canned answers after denial — we found and fixed that).
- *What isn't covered?* See `docs/threat-model.md` → Limitations.
