/**
 * Overview of the simulated demo target.
 * Posture = latest completed result per attack case / benign task under the target's ACTIVE policy
 * (backend engine/posture.py). Coverage and attention lists come from /findings, /scenarios, /attack-cases.
 */
import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "../api/client";
import type { AttackCase, DashboardSummary, Finding, Page, ScenarioSpec } from "../api/models";
import { DemoRunner } from "../components/demo/DemoRunner";
import { Badge } from "../components/ui/Badge";
import { Card, CardTitle } from "../components/ui/Card";
import { PageState } from "../components/ui/PageState";
import { SeverityBadge } from "../components/ui/SeverityBadge";
import { runOutcome, STATUS_LABEL } from "../lib/status";

const Metric: React.FC<{ to: string; label: string; value: React.ReactNode; note: string; tone?: "vuln" | "ok" | "neutral" }> = ({
  to,
  label,
  value,
  note,
  tone = "neutral",
}) => (
  <Link to={to} className="group rounded-lg border border-line bg-surface p-4 hover:border-line-strong transition-colors duration-150">
    <p className="text-xs text-ink-2">{label}</p>
    <p className={`mt-1 text-2xl font-semibold font-mono tabular-nums ${tone === "vuln" ? "text-vuln" : tone === "ok" ? "text-term" : "text-ink"}`}>
      {value}
    </p>
    <p className="mt-1 text-[11px] leading-4 text-ink-3 group-hover:text-ink-2">{note}</p>
  </Link>
);

const SEV_ORDER = ["critical", "high", "medium", "low"];

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const summary = useApi<DashboardSummary>("/dashboard/summary");
  const findings = useApi<Page<Finding>>("/findings?limit=200");
  const scenarios = useApi<ScenarioSpec[]>("/scenarios");
  const cases = useApi<AttackCase[]>("/attack-cases");
  const refresh = () => {
    void summary.refetch();
    void findings.refetch();
  };

  const d = summary.data;
  if (summary.loading || summary.error || !d) {
    return <PageState loading={summary.loading} error={summary.error} rows={6} />;
  }

  const all = findings.data?.items ?? [];
  const attention = all
    .filter((f) => f.status === "open" || f.status === "regressed")
    .sort((a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity));
  const tested = d.total_attacks > 0 || d.total_benign > 0;
  const sev = d.findings_by_severity;
  const sevMax = Math.max(1, ...Object.values(sev));

  return (
    <div className="max-w-7xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-ink">Overview</h1>
          <p className="text-sm text-ink-2 max-w-prose">
            Posture of the simulated target under its active policy <span className="font-mono text-ink">{d.active_policy_id ?? "none"}</span>. Every number links to the records behind it.
          </p>
        </div>
        {tested && <DemoRunner onDone={refresh} />}
      </div>

      {!tested && (
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-ink">Nothing has been tested yet</h2>
          <ol className="mt-3 grid gap-3 sm:grid-cols-3 text-xs text-ink-2">
            <li><span className="font-medium text-ink">1. Attack.</span> Seven attacks run against the simulated agent; success is read from state diffs and canaries only.</li>
            <li><span className="font-medium text-ink">2. Trace and price.</span> Each exploit is traced to the tool permission behind it, and each fix gets a measured price tag.</li>
            <li><span className="font-medium text-ink">3. Fix and retest.</span> Zero-cost fixes are applied and every attack and benign task is re-measured.</li>
          </ol>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <DemoRunner variant="primary" onDone={refresh} />
            <span className="text-xs text-ink-3">Takes about 30 seconds. Or start a single attack with New run.</span>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Metric
          to="/runs"
          label="Attacks succeeding now"
          value={`${d.successful_attacks}/${d.total_attacks}`}
          note={`Latest result per case; AS-05 via the sleeper chain (${d.sleeper_outcome ?? "not run"})`}
          tone={d.successful_attacks ? "vuln" : d.total_attacks ? "ok" : "neutral"}
        />
        <Metric
          to="/runs"
          label="Benign tasks passing"
          value={`${d.passed_benign}/${d.total_benign}`}
          note={d.inconclusive ? `${d.inconclusive} inconclusive runs not counted` : "No inconclusive runs"}
          tone={d.total_benign && d.passed_benign === d.total_benign ? "ok" : "neutral"}
        />
        <Metric to="/findings" label="Findings needing attention" value={d.open_findings} note="Open or regressed" tone={d.open_findings ? "vuln" : "neutral"} />
        <Metric to="/permissions" label="Grants hardened" value={d.fixes_applied} note="Tools removed or constrained since the first tested policy" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="p-0 sm:p-0 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-line">
            <CardTitle>Findings needing attention</CardTitle>
            <Link to="/findings" className="text-xs text-action hover:underline">
              All findings
            </Link>
          </div>
          <div className="px-4">
            <PageState loading={findings.loading} error={findings.error} rows={3} />
          </div>
          {findings.data && !attention.length && (
            <p className="px-4 py-6 text-sm text-ink-2">
              Nothing open. {all.length ? `${all.length} recorded findings are fixed or accepted.` : "No findings recorded yet."}
            </p>
          )}
          <ul className="divide-y divide-line">
            {attention.map((f) => (
              <li key={f.id}>
                <Link to={`/findings/${f.id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-surface-muted">
                  <SeverityBadge severity={f.severity} />
                  <span className="font-mono text-xs text-ink-2 w-12 shrink-0">{f.case_id}</span>
                  <span className="text-sm text-ink truncate">{f.title}</span>
                  <Badge variant={STATUS_LABEL[f.status].variant} className="ml-auto">
                    {STATUS_LABEL[f.status].label}
                  </Badge>
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>Recorded findings by severity</CardTitle>
          <p className="text-xs text-ink-3 mt-0.5 mb-3">All statuses, including fixed</p>
          <ul className="space-y-2">
            {(["critical", "high", "medium", "low"] as const).map((k) => (
              <li key={k} className="grid grid-cols-[64px_1fr_24px] items-center gap-2 text-xs">
                <span className="text-ink-2 capitalize">{k}</span>
                <span className="h-2 rounded-sm bg-surface-muted overflow-hidden" aria-hidden>
                  <span
                    className={`block h-full ${k === "critical" ? "bg-vuln" : k === "low" ? "bg-info" : "bg-warn"}`}
                    style={{ width: `${((sev[k] ?? 0) / sevMax) * 100}%` }}
                  />
                </span>
                <span className="font-mono tabular-nums text-right text-ink">{sev[k] ?? 0}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="p-0 sm:p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-line">
          <CardTitle>Attack coverage by scenario</CardTitle>
          <p className="text-xs text-ink-3 mt-0.5">Cases defined in the acme suite and how many produced a confirmed finding</p>
        </div>
        <div className="px-4">
          <PageState loading={scenarios.loading || cases.loading} error={scenarios.error || cases.error} rows={2} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-muted text-ink-2">
              <tr>
                <th scope="col" className="px-4 py-2 font-medium">Scenario</th>
                <th scope="col" className="px-4 py-2 font-medium">Cases</th>
                <th scope="col" className="px-4 py-2 font-medium">Confirmed findings</th>
                <th scope="col" className="px-4 py-2 font-medium">Open now</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {(scenarios.data ?? []).map((s) => {
                const ids = (cases.data ?? []).filter((c) => c.scenario_id === s.id).map((c) => c.id);
                const fs = all.filter((f) => f.scenario_id === s.id);
                const open = fs.filter((f) => f.status === "open" || f.status === "regressed").length;
                return (
                  <tr key={s.id}>
                    <td className="px-4 py-2 text-ink">{s.name}</td>
                    <td className="px-4 py-2 font-mono text-ink-2">{ids.join(", ") || "none"}</td>
                    <td className="px-4 py-2 font-mono text-ink">{fs.length}</td>
                    <td className={`px-4 py-2 font-mono ${open ? "text-vuln" : "text-ink-2"}`}>{open}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="p-0 sm:p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-line">
          <CardTitle>Recent runs</CardTitle>
          <p className="text-xs text-ink-3 mt-0.5">
            All policies, including baseline, counterfactual and fix-measurement runs. AS-05 rows are single sleeper sessions; the chain outcome drives posture.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-muted text-ink-2">
              <tr>
                <th scope="col" className="px-4 py-2 font-medium">Run</th>
                <th scope="col" className="px-4 py-2 font-medium">Case or task</th>
                <th scope="col" className="px-4 py-2 font-medium">Policy</th>
                <th scope="col" className="px-4 py-2 font-medium">Outcome</th>
                <th scope="col" className="px-4 py-2 font-medium">Severity</th>
                <th scope="col" className="px-4 py-2 font-medium">Finished</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {d.recent_runs.map((r) => {
                const o = runOutcome(r);
                return (
                  <tr key={r.id} className="cursor-pointer hover:bg-surface-muted" onClick={() => navigate(`/runs/${r.id}`)}>
                    <td className="px-4 py-2 font-mono">
                      <Link to={`/runs/${r.id}`} onClick={(e) => e.stopPropagation()} className="text-action hover:underline">
                        {r.id}
                      </Link>
                    </td>
                    <td className="px-4 py-2 font-mono text-ink">{r.case_id ?? r.user_task_id}</td>
                    <td className="px-4 py-2 font-mono text-ink-2">{r.policy_id}</td>
                    <td className="px-4 py-2">
                      <Badge variant={o.variant}>{o.label}</Badge>
                    </td>
                    <td className="px-4 py-2">
                      {r.verdict_success && r.severity && r.severity !== "none" ? <SeverityBadge severity={r.severity} /> : <span className="text-ink-3">n/a</span>}
                    </td>
                    <td className="px-4 py-2 text-ink-2 whitespace-nowrap">{r.finished_at ? new Date(r.finished_at).toLocaleTimeString() : "n/a"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
