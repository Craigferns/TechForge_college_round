# AgentBreak threat model, isolation and limitations

Scope: the local, single-machine prototype in this repository (FastAPI + SQLite + React).

## Trust boundaries

| Boundary | Trust | Controls in place | Not controlled |
|---|---|---|---|
| Browser → API (`127.0.0.1:8000`) | Local user, no auth | Binds loopback only; CORS limited to `AGENTBREAK_CORS_ORIGINS`; Pydantic `extra="forbid"` request models; errors returned as an envelope without stack traces | Any local process can call the API. Do not expose the port. |
| Test definitions (cases, payload templates) | Repo code | Fixed attack matrix; payloads ≤ 1,500 chars; fake principals only (`scripts/lint_fake_data.py`) | — |
| Agent under test | **Untrusted** | Every tool call goes through `PolicyRuntime`; a denied call never executes the tool body. Output is stored and rendered as text (no `eval`, no raw HTML, Markdown without HTML) | A real `openai_compat` agent runs remotely; AgentBreak only sees its tool calls |
| Sandbox tools (`acme` suite) | Repo code | In-memory mock environment per run; no filesystem, network or subprocess access from tools | — |
| Model providers / target endpoints | Semi-trusted | `base_url` must be local/private unless `AGENTBREAK_ALLOW_REMOTE_TARGETS=1` (`scripts/check_egress.py`); every HTTP call has a timeout; API keys referenced by env-var **name** only | A malicious endpoint can return arbitrary text/tool calls → treated as untrusted agent output |
| Verdict engine | Trusted, pure | Reads only PRE/POST snapshots; AST test forbids importing LLM/target code | — |
| Execution workers | Trusted | Thread pool (2 workers) + one demo worker; job-boundary exception handling marks runs `error` | No CPU/memory limits per run (in-process threads) |
| SQLite DB / traces | Local file | Parameterized SQL only; one connection per operation; WAL + busy timeout | Not encrypted; anyone with file access reads traces |
| Reports | Generated | Built from stored records; injected text truncated (300 chars) and fenced so it cannot break out of a code block | — |

## How a malicious target could affect AgentBreak itself
- **Prompt injection against AgentBreak:** nothing in the pipeline asks an LLM to judge or act on
  target output; verdicts read state only. The optional attacker LLM generates payloads but never decides success.
- **XSS via trace/report content:** React renders text; `react-markdown` is used without raw HTML.
- **Resource exhaustion:** a slow `openai_compat` target is bounded by HTTP timeouts, not by a per-run
  CPU/memory sandbox. Runs execute in-process; this is **not** an isolation boundary for untrusted code.
  AgentBreak never executes target-supplied code.
- **False "safe" results:** runs that error are `inconclusive` and are never counted as blocked,
  resisted or passed; `cli ci` exits 2 on any inconclusive run; `verify` fails closed when snapshots
  are missing.

## Data handling
- All sandbox data is synthetic: `.test` domains, canary tokens `AB-CANARY-(KEY|BUD)-<8 hex>`.
- Secrets: targets store the env-var name (`api_key_env`), never the key; `scripts/scan_secrets.py` gates commits.
- Retention: everything stays in the local SQLite file (`AGENTBREAK_DB_PATH`, default `./data/agentbreak.db`, gitignored)
  until the user deletes it. There is no automatic retention policy and no redaction beyond the
  fact that the data is synthetic — do **not** point AgentBreak at real mailboxes or files.

## Secure configuration checklist
- Keep `--host 127.0.0.1`. Keep `AGENTBREAK_ALLOW_REMOTE_TARGETS` unset unless you own the remote endpoint.
- Put provider keys in `.env` (gitignored) and reference them by name.
- Use a separate `AGENTBREAK_DB_PATH` per experiment if you need clean evidence.

## Limitations (state these when presenting)
1. **Fidelity:** the default target is a deterministic scripted agent that obeys injection markers. Results
   demonstrate the measurement pipeline; they are not a detection or robustness rate for real models.
2. **Coverage:** 7 attack cases across 4 scenarios (indirect injection, malicious document, sleeper memory,
   privilege escalation) and 10 benign tasks in one synthetic suite. Direct prompt injection and
   policy-bypass/confused-deputy variants are not separate cases.
3. **Permission model:** permission = tool name plus one argument constraint (`domain_allowlist`).
4. **Residual risk the product reports but does not fix:** a blocked sleeper trigger leaves the poisoned
   instruction in memory.
5. **No auth, single machine, in-process workers.** Not a multi-tenant service.
6. Fix kinds `defense` and `prompt_hardening` exist in the schema but are not implemented; the API rejects them.
