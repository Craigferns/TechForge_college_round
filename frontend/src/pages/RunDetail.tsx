/**
 * Run investigation: verdict summary → attack path → trace timeline ⇄ step detail → evidence / state diff.
 * Selection is shared: picking a path node selects its trace step and vice versa.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Eye, ShieldCheck } from "lucide-react";
import { apiClient, useApi, useByIdOrLatest } from "../api/client";
import type { AttackGraph, Run, SnapshotPair, TraceStep, Verdict } from "../api/models";
import { AttackPath } from "../components/run/AttackPath";
import { StateDiff } from "../components/run/StateDiff";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, CardTitle } from "../components/ui/Card";
import { CopyButton } from "../components/ui/CopyButton";
import { PageState } from "../components/ui/PageState";
import { SeverityBadge } from "../components/ui/SeverityBadge";

type Filter = "all" | "flagged" | "tool_call" | "tool_result" | "messages";
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "flagged", label: "Flagged" },
  { id: "tool_call", label: "Tool calls" },
  { id: "tool_result", label: "Tool results" },
  { id: "messages", label: "Messages" },
];

function outcome(run: Run): { label: string; variant: "unauthorized" | "allowed" | "medium" | "inconclusive" | "running" } {
  if (run.status === "error") return { label: "Inconclusive (run errored)", variant: "inconclusive" };
  if (run.status !== "done") return { label: run.status, variant: "running" };
  if (run.kind === "benign") return run.utility ? { label: "Benign pass", variant: "allowed" } : { label: "Benign fail", variant: "medium" };
  if (run.verdict?.success) return { label: "Exploited", variant: "unauthorized" };
  return { label: `Not exploited (${(run.verdict?.classification ?? "no verdict").replace(/_/g, " ")})`, variant: "allowed" };
}

const StepFlags: React.FC<{ s: TraceStep }> = ({ s }) => (
  <>
    {s.flags?.injected && <Badge variant="injected">Injected content</Badge>}
    {s.flags?.unauthorized && <Badge variant="unauthorized">Unauthorized</Badge>}
    {s.flags?.denied && <Badge variant="denied">Denied by policy</Badge>}
  </>
);

export const RunDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const [params] = useSearchParams();
  const caseId = params.get("case");
  const runRes = useByIdOrLatest<Run>("/runs", runId, `&kind=attack${caseId ? `&case_id=${encodeURIComponent(caseId)}` : ""}`);
  const run = runRes.data;
  const id = runRes.id;
  const trace = useApi<TraceStep[]>(id ? `/runs/${id}/trace` : null);
  const snapshots = useApi<SnapshotPair>(id ? `/runs/${id}/snapshots` : null);
  const graph = useApi<AttackGraph>(id ? `/runs/${id}/graph` : null);

  const [selected, setSelected] = useState<number | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [tab, setTab] = useState<"evidence" | "diff" | "repro">("evidence");
  const [verify, setVerify] = useState<{ state: "idle" | "busy" } | { state: "done"; v: Verdict } | { state: "error"; msg: string }>({ state: "idle" });
  const listRef = useRef<HTMLOListElement>(null);

  // Default selection: the first flagged step (the interesting one), else the first step.
  useEffect(() => {
    if (!trace.data?.length) return;
    const flagged = trace.data.find((s) => s.flags?.unauthorized || s.flags?.injected);
    setSelected((flagged ?? trace.data[0]).idx);
    setVerify({ state: "idle" });
  }, [trace.data]);

  const visible = useMemo(
    () =>
      (trace.data ?? []).filter((s) =>
        filter === "all"
          ? true
          : filter === "flagged"
            ? s.flags?.injected || s.flags?.unauthorized || s.flags?.denied
            : filter === "messages"
              ? s.kind !== "tool_call" && s.kind !== "tool_result"
              : s.kind === filter
      ),
    [trace.data, filter]
  );
  const step = trace.data?.find((s) => s.idx === selected) ?? null;

  const selectStep = (idx: number) => {
    setSelected(idx);
    if (!visible.some((s) => s.idx === idx)) setFilter("all"); // keep the selection visible
    requestAnimationFrame(() => listRef.current?.querySelector<HTMLElement>(`[data-idx="${idx}"]`)?.scrollIntoView({ block: "nearest" }));
  };

  const onListKey = (e: React.KeyboardEvent) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const pos = visible.findIndex((s) => s.idx === selected);
    const next = visible[Math.min(visible.length - 1, Math.max(0, pos + (e.key === "ArrowDown" ? 1 : -1)))];
    if (next) {
      setSelected(next.idx);
      listRef.current?.querySelector<HTMLElement>(`[data-idx="${next.idx}"]`)?.focus();
    }
  };

  const runVerify = async () => {
    if (!id) return;
    setVerify({ state: "busy" });
    try {
      setVerify({ state: "done", v: await apiClient<Verdict>(`/runs/${id}/verify`, { method: "POST" }) });
    } catch (e) {
      setVerify({ state: "error", msg: e instanceof Error ? e.message : String(e) });
    }
  };

  if (runRes.loading || runRes.error || runRes.empty || !run) {
    return (
      <PageState
        loading={runRes.loading}
        error={runRes.error}
        empty={runRes.empty || !run}
        emptyText="No attack runs recorded yet. Start one with New run, or run the full demo from the Overview."
        rows={6}
      />
    );
  }

  const o = outcome(run);
  const verifyCmd = `uv run python -m agentbreak.cli verify ${id}`;

  return (
    <div className="max-w-7xl space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-lg font-semibold text-ink font-mono truncate">{id}</h1>
            <Badge variant={o.variant}>{o.label}</Badge>
            {run.verdict?.success && run.verdict.severity && run.verdict.severity !== "none" && <SeverityBadge severity={run.verdict.severity} />}
          </div>
          <p className="text-xs text-ink-2">
            {run.case_id ? (
              <>
                Case <span className="font-mono text-ink">{run.case_id}</span> ({run.scenario_id}), carrier task{" "}
              </>
            ) : (
              "Benign task "
            )}
            <span className="font-mono text-ink">{run.user_task_id}</span>, policy <span className="font-mono text-ink">{run.policy_id}</span>
            {run.repro?.sleeper_id ? (
              <>
                , {String(run.repro.session)} session of sleeper chain{" "}
                <Link className="font-mono text-action hover:underline" to={`/sleeper/${String(run.repro.sleeper_id)}`}>
                  {String(run.repro.sleeper_id)}
                </Link>
              </>
            ) : null}
            {run.started_at && run.finished_at && (
              <>, took {Math.max(1, Math.round(new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()))} ms</>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to={`/visualizer${run.case_id ? `?case=${run.case_id}` : ""}`}>
            <Button variant="secondary" size="sm" icon={<Eye className="w-3.5 h-3.5" />}>
              Simulate in visualizer
            </Button>
          </Link>
          <Link to="/permissions" className="text-xs text-action hover:underline">
            Which permission enabled this
          </Link>
          <Button variant="secondary" size="sm" icon={<ShieldCheck className="w-3.5 h-3.5" />} loading={verify.state === "busy"} onClick={runVerify} disabled={!run.verdict}>
            Re-verify verdict
          </Button>
        </div>
      </div>

      {run.error && (
        <p role="alert" className="text-xs rounded-md border border-infra/35 bg-infra/5 p-2.5 text-ink">
          Run error: <span className="font-mono">{run.error}</span>. Inconclusive runs are never counted as blocked or passed.
        </p>
      )}
      {verify.state === "done" && (
        <p role="status" className={`text-xs rounded-md border p-2.5 text-ink ${verify.v.matches_stored ? "border-ok/40 bg-ok/5" : "border-vuln/40 bg-vuln/5"}`}>
          {verify.v.matches_stored
            ? "Match: the verdict recomputed from the stored PRE/POST snapshots equals the stored verdict hash."
            : "Mismatch: the recomputed verdict differs from the stored one. Treat this run's verdict as unreliable."}{" "}
          <span className="font-mono text-ink-3 break-all">{verify.v.verdict_hash}</span>
        </p>
      )}
      {verify.state === "error" && (
        <p role="alert" className="text-xs rounded-md border border-infra/35 bg-infra/5 p-2.5 text-ink">
          Verification could not run: {verify.msg}
        </p>
      )}

      {run.kind === "attack" && (
        <Card>
          <CardTitle className="mb-3">Attack path</CardTitle>
          <PageState loading={graph.loading} error={graph.error} rows={1} />
          {graph.data && <AttackPath graph={graph.data} verdict={run.verdict} selectedStep={selected} onSelectStep={selectStep} />}
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <Card className="p-0 sm:p-0 overflow-hidden flex flex-col max-h-[70vh]">
          <div className="px-4 py-3 border-b border-line space-y-2">
            <CardTitle>Execution trace</CardTitle>
            <div className="flex flex-wrap gap-1" role="group" aria-label="Filter trace steps">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  aria-pressed={filter === f.id}
                  onClick={() => setFilter(f.id)}
                  className={`rounded px-2 py-0.5 text-[11px] ring-1 ring-inset transition-colors duration-150 ${
                    filter === f.id ? "bg-action/10 text-action ring-action/40" : "text-ink-2 ring-line-strong hover:text-ink"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
          <div className="px-4">
            <PageState loading={trace.loading} error={trace.error} rows={5} />
          </div>
          <ol ref={listRef} className="overflow-y-auto divide-y divide-line" onKeyDown={onListKey} aria-label="Trace steps">
            {visible.map((s) => {
              const isSel = s.idx === selected;
              return (
                <li key={s.idx}>
                  <button
                    data-idx={s.idx}
                    onClick={() => setSelected(s.idx)}
                    aria-current={isSel ? "step" : undefined}
                    className={`w-full text-left px-4 py-2 flex items-start gap-2.5 transition-colors duration-150 ${
                      isSel ? "bg-action/10 shadow-[inset_2px_0_0_rgb(var(--action-primary))]" : "hover:bg-surface-muted"
                    }`}
                  >
                    <span className="font-mono text-[11px] text-ink-3 w-6 shrink-0 pt-0.5">{s.idx}</span>
                    <span className="min-w-0 space-y-1">
                      <span className="block text-xs text-ink">
                        <span className="text-ink-2">{s.kind.replace("_", " ")}</span>
                        {s.tool && <span className="font-mono"> {s.tool}</span>}
                      </span>
                      <span className="flex flex-wrap gap-1">
                        <StepFlags s={s} />
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
            {trace.data && !visible.length && <li className="px-4 py-4 text-xs text-ink-2">No steps match this filter.</li>}
          </ol>
        </Card>

        <div className="space-y-4 min-w-0">
          <Card>
            {step ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle>
                    Step {step.idx}: {step.kind.replace("_", " ")}
                    {step.tool && <span className="font-mono font-normal"> {step.tool}</span>}
                  </CardTitle>
                  <StepFlags s={step} />
                  {step.caused_by_idx != null && (
                    <button className="text-[11px] text-action hover:underline" onClick={() => selectStep(step.caused_by_idx as number)}>
                      caused by step {step.caused_by_idx}
                    </button>
                  )}
                </div>
                {step.args && (
                  <div>
                    <div className="flex items-center justify-between">
                      <p className="text-[11px] text-ink-3">Arguments</p>
                      <CopyButton text={JSON.stringify(step.args, null, 2)} label="Copy arguments" />
                    </div>
                    <pre className="mt-1 overflow-x-auto rounded-md border border-line bg-surface-muted p-2.5 text-[12px] leading-relaxed text-term">
                      {JSON.stringify(step.args, null, 2)}
                    </pre>
                  </div>
                )}
                {step.content && (
                  <div>
                    <div className="flex items-center justify-between">
                      <p className="text-[11px] text-ink-3">{step.flags?.injected ? "Content (untrusted, contains injected text)" : "Content"}</p>
                      <CopyButton text={step.content} label="Copy content" />
                    </div>
                    <pre
                      className={`mt-1 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-md border p-2.5 text-[12px] leading-relaxed text-ink ${
                        step.flags?.injected ? "border-warn/40 bg-warn/5" : "border-line bg-surface-muted"
                      }`}
                    >
                      {step.content}
                    </pre>
                  </div>
                )}
                {!step.args && !step.content && <p className="text-xs text-ink-2">This step recorded no arguments or content.</p>}
              </div>
            ) : (
              <p className="text-xs text-ink-2">Select a trace step.</p>
            )}
          </Card>

          <Card className="space-y-3">
            <div className="flex gap-1 border-b border-line -mx-4 sm:-mx-5 px-4 sm:px-5" role="tablist" aria-label="Run evidence">
              {(
                [
                  ["evidence", "Verdict evidence"],
                  ["diff", "State diff"],
                  ["repro", "Reproduce"],
                ] as const
              ).map(([k, label]) => (
                <button
                  key={k}
                  role="tab"
                  aria-selected={tab === k}
                  onClick={() => setTab(k)}
                  className={`-mb-px border-b-2 px-2.5 py-2 text-xs transition-colors duration-150 ${
                    tab === k ? "border-action text-ink font-medium" : "border-transparent text-ink-2 hover:text-ink"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div role="tabpanel">
              {tab === "evidence" &&
                (run.verdict ? (
                  <div className="space-y-2 text-xs">
                    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                      <dt className="text-ink-3">Classification</dt>
                      <dd className={`font-mono ${run.verdict.success ? "text-vuln" : "text-term"}`}>{run.verdict.classification}</dd>
                      <dt className="text-ink-3">Impact</dt>
                      <dd className="font-mono text-ink">{run.verdict.impact_class ?? "none"}</dd>
                      <dt className="text-ink-3">Verdict hash</dt>
                      <dd className="font-mono text-ink-2 break-all">{run.verdict.verdict_hash}</dd>
                    </dl>
                    {run.verdict.evidence?.length ? (
                      <ul className="space-y-1.5">
                        {run.verdict.evidence.map((e, i) => (
                          <li key={i} className="rounded-md border border-line bg-surface-muted p-2">
                            <span className="font-mono text-term">{e.type}</span> <span className="font-mono text-ink-3">{e.path}</span>
                            <span className="block text-ink mt-0.5">{e.detail}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-ink-2">No state-diff or canary evidence: nothing protected changed.</p>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-ink-2">No verdict recorded for this run.</p>
                ))}
              {tab === "diff" && (
                <>
                  <PageState loading={snapshots.loading} error={snapshots.error} rows={3} />
                  {snapshots.data && <StateDiff pre={snapshots.data.pre} post={snapshots.data.post} />}
                </>
              )}
              {tab === "repro" && (
                <div className="space-y-2 text-xs">
                  <p className="text-ink-2">Recompute this verdict from the stored snapshots. Exit 0 means it matches the stored hash.</p>
                  <div className="flex items-center justify-between gap-2 rounded-md border border-line bg-surface-muted px-2.5 py-1.5">
                    <code className="text-term break-all">{verifyCmd}</code>
                    <CopyButton text={verifyCmd} label="Copy verify command" />
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
