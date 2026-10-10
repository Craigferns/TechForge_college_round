/**
 * Permission analysis (D1). Every column is measured:
 * "used by benign" = allowed calls in passing benign runs; "enables" = exploits that stop succeeding
 * when only that tool is removed (counterfactual re-run); "cost" = benign tasks that then fail.
 */
import React, { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiClient, useApi, useByIdOrLatest } from "../api/client";
import type { PermissionAudit, PolicyDiff, Target } from "../api/models";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, CardTitle } from "../components/ui/Card";
import { PageState } from "../components/ui/PageState";

export const PermissionDiffPage: React.FC = () => {
  const { auditId } = useParams<{ auditId: string }>();
  const navigate = useNavigate();
  const audit = useByIdOrLatest<PermissionAudit>("/audits", auditId);
  const target = useApi<Target>(audit.data ? `/targets/${audit.data.target_id}` : "/targets/tgt_demo_scripted");
  const active = target.data?.active_policy_id;
  const diff = useApi<PolicyDiff>(audit.data && active && active !== audit.data.policy_id ? `/policies/${audit.data.policy_id}/diff/${active}` : null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const runAudit = async () => {
    setStarting(true);
    setStartError(null);
    try {
      const created = await apiClient<PermissionAudit>("/audits", {
        method: "POST",
        body: JSON.stringify({ target_id: target.data?.id ?? "tgt_demo_scripted", policy_id: active ?? "pol_full" }),
      });
      navigate(`/permissions/${created.id}`);
    } catch (e) {
      setStartError(e instanceof Error ? e.message : String(e));
    } finally {
      setStarting(false);
    }
  };

  const a = audit.data;
  const header = (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-lg font-semibold text-ink">Permission analysis</h1>
        <p className="text-sm text-ink-2 max-w-prose">
          Which tool grant enabled which exploit, measured by removing one tool at a time and re-running every attack and benign task.
        </p>
      </div>
      <Button variant="secondary" size="sm" loading={starting} onClick={runAudit} disabled={!target.data}>
        Audit active policy
      </Button>
    </div>
  );

  if (audit.loading || audit.error || audit.empty || !a) {
    return (
      <div className="max-w-7xl space-y-4">
        {header}
        <PageState
          loading={audit.loading}
          error={audit.error ?? startError}
          empty={audit.empty || !a}
          emptyText="No permission audit yet. An audit re-runs all attacks and benign tasks once per granted tool."
          rows={6}
        />
      </div>
    );
  }

  const proofOk = !!a.proof && a.proof.benign_pass_under_minimal === a.proof.benign_total;
  const granted = a.granted ?? [];
  const needed = a.needed ?? [];
  const excess = a.excess ?? [];
  const rows = a.rows ?? [];

  return (
    <div className="max-w-7xl space-y-4">
      {header}
      {startError && <PageState error={startError} />}
      {a.status !== "done" && (
        <p role="status" className="text-xs rounded-md border border-infra/35 bg-infra/5 p-2.5 text-ink">
          Audit status {a.status}: {a.stage}
        </p>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          ["Granted", granted.length, `by policy ${a.policy_id}`],
          ["Needed", needed.length, "called by passing benign runs"],
          ["Excess", excess.length, excess.join(", ") || "none"],
          ["Minimal policy keeps", a.proof ? `${a.proof.benign_pass_under_minimal}/${a.proof.benign_total}` : "n/a", `benign tasks passing (${a.minimal_policy_id ?? "no policy"})`],
        ].map(([label, value, note]) => (
          <div key={label as string} className="rounded-lg border border-line bg-surface p-4">
            <p className="text-xs text-ink-2">{label}</p>
            <p
              className={`mt-1 text-2xl font-semibold font-mono tabular-nums ${
                label === "Excess" && excess.length ? "text-warn-ink" : label === "Minimal policy keeps" ? (proofOk ? "text-term" : "text-warn-ink") : "text-ink"
              }`}
            >
              {value}
            </p>
            <p className="mt-1 text-[11px] text-ink-3 truncate">{note}</p>
          </div>
        ))}
      </div>

      <Card className="p-0 sm:p-0 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line">
          <div>
            <CardTitle>Tool grants of {a.policy_id}</CardTitle>
            <p className="text-xs text-ink-3 mt-0.5">Audit {a.id}</p>
          </div>
          <Link to={`/fixes/${a.id}`} className="text-xs font-medium text-action hover:underline">
            Measure fixes in Remediation
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-muted text-ink-2">
              <tr>
                <th scope="col" className="px-4 py-2 font-medium">Tool</th>
                <th scope="col" className="px-4 py-2 font-medium">Status</th>
                <th scope="col" className="px-4 py-2 font-medium">Used by benign tasks</th>
                <th scope="col" className="px-4 py-2 font-medium">Exploits enabled (blocked when removed)</th>
                <th scope="col" className="px-4 py-2 font-medium">Benign broken if removed</th>
                <th scope="col" className="px-4 py-2 font-medium">Evidence-derived scope</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => {
                const cf = (r.enabled_exploits ?? []).find((e) => e.counterfactual)?.counterfactual;
                return (
                  <tr key={r.tool} className={r.status === "excess" ? "bg-warn/5" : ""}>
                    <td className="px-4 py-2 font-mono text-ink">{r.tool}</td>
                    <td className="px-4 py-2">
                      <Badge variant={r.status === "excess" ? "high" : "outline"}>{r.status === "excess" ? "Excess" : "Needed"}</Badge>
                    </td>
                    <td className="px-4 py-2 font-mono text-ink-2">{r.used_by_benign.join(", ") || "none"}</td>
                    <td className="px-4 py-2">
                      <span className="flex flex-wrap gap-1">
                        {(r.enabled_exploits ?? []).length
                          ? (r.enabled_exploits ?? []).map((e) => (
                              <Link key={e.case_id} to={`/runs?case=${e.case_id}`} className="font-mono text-vuln hover:underline" title={e.role === "observed" ? "Observed in the exploit run (no counterfactual)" : "Counterfactual: blocked when this tool is removed"}>
                                {e.case_id}
                                {e.role === "observed" ? "*" : ""}
                              </Link>
                            ))
                          : <span className="text-ink-3">none</span>}
                      </span>
                    </td>
                    <td className={`px-4 py-2 font-mono ${cf ? (cf.benign_broken ? "text-warn-ink" : "text-term") : "text-ink-3"}`}>
                      {cf ? `${cf.benign_broken}` : "n/a"}
                    </td>
                    <td className="px-4 py-2 font-mono text-ink-2">
                      {r.suggested_scope ? `${r.suggested_scope.args.join(", ")} ∈ {${r.suggested_scope.domain_allowlist.join(", ")}}` : "n/a"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardTitle>Audited policy versus active policy</CardTitle>
        <p className="text-xs text-ink-3 mt-0.5 mb-3">
          <span className="font-mono">{a.policy_id}</span> → <span className="font-mono">{active ?? "unknown"}</span>
        </p>
        {!active || active === a.policy_id ? (
          <p className="text-xs text-ink-2">The audited policy is still active: no fix has been applied since this audit.</p>
        ) : (
          <>
            <PageState loading={diff.loading} error={diff.error} rows={2} />
            {diff.data && (
              <ul className="space-y-1 font-mono text-xs">
                {diff.data.removed_tools.map((t) => (
                  <li key={t} className="text-vuln">
                    <span aria-hidden>− </span>
                    <span className="sr-only">Removed </span>
                    {t}
                  </li>
                ))}
                {diff.data.added_tools.map((t) => (
                  <li key={t} className="text-term">
                    <span aria-hidden>+ </span>
                    <span className="sr-only">Added </span>
                    {t}
                  </li>
                ))}
                {diff.data.constraint_changes.map((c) => (
                  <li key={c.tool} className="text-warn-ink">
                    <span aria-hidden>~ </span>
                    <span className="sr-only">Constrained </span>
                    {c.tool}: <span className="text-ink-2">{c.before}</span> → <span className="text-ink">{c.after}</span>
                  </li>
                ))}
                {!diff.data.removed_tools.length && !diff.data.added_tools.length && !diff.data.constraint_changes.length && (
                  <li className="text-ink-2 font-sans">No grant differences.</li>
                )}
              </ul>
            )}
            <p className="mt-3 text-xs text-ink-2">
              Whether these changes worked is measured, not assumed: see the posture on the Overview or re-run the CI gate.
            </p>
          </>
        )}
      </Card>
    </div>
  );
};
