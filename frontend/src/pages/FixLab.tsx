/**
 * Remediation (D2). Three distinct states, never conflated:
 *   suggested  – derived from audit evidence, not yet measured
 *   measured   – every attack and benign task re-run under base and fixed policy (the price tag)
 *   applied    – the measured result policy is the target's active policy
 * Findings only become "fixed" from a measured evaluation (backend apply_fix_eval).
 */
import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronDown, ChevronRight, FlaskConical, RotateCcw } from "lucide-react";
import { apiClient, useApi, useByIdOrLatest } from "../api/client";
import type { FixEval, FixSuggestion, Page, PermissionAudit, Policy, Target } from "../api/models";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, CardTitle } from "../components/ui/Card";
import { Modal } from "../components/ui/Modal";
import { PageState } from "../components/ui/PageState";
import { BeforeAfter } from "../components/fix/BeforeAfter";

function fixLabel(f: FixEval["fix"]): string {
  if (f.kind === "remove_permission") return `remove ${f.tool}`;
  return `restrict ${f.tool} [${(f.args ?? []).join(", ")}] to ${(f.domains ?? []).join(", ")}`;
}

const Ids: React.FC<{ label: string; ids?: string[]; tone: string }> = ({ label, ids, tone }) => (
  <div>
    <dt className="text-ink-3">{label}</dt>
    <dd className={`font-mono ${ids?.length ? tone : "text-ink-3"}`}>{ids?.length ? ids.join(", ") : "none"}</dd>
  </div>
);

export const FixLabPage: React.FC = () => {
  const { auditId } = useParams<{ auditId: string }>();
  const audit = useByIdOrLatest<PermissionAudit>("/audits", auditId);
  const aid = audit.id;
  const suggestions = useApi<FixSuggestion[]>(aid ? `/audits/${aid}/fixes` : null);
  const evals = useApi<Page<FixEval>>(aid ? `/fix-evals?audit_id=${aid}&limit=200` : null);
  const target = useApi<Target>(audit.data ? `/targets/${audit.data.target_id}` : null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<FixEval | null>(null);

  const act = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key);
    setActionError(null);
    try {
      await fn();
      await Promise.all([evals.refetch(), target.refetch()]);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const measure = (s: FixSuggestion) =>
    act(s.id, () =>
      apiClient<FixEval>("/fix-evals", {
        method: "POST",
        body: JSON.stringify({ target_id: audit.data?.target_id, base_policy_id: audit.data?.policy_id, fix: s.fix }),
      })
    );

  const apply = (f: FixEval) => {
    setConfirm(null);
    return act(`apply-${f.id}`, async () => {
      const pol = await apiClient<Policy>(`/fix-evals/${f.id}/apply`, { method: "POST" });
      setNotice(`Policy ${pol.id} is now active. Findings for ${f.details?.blocked_cases?.join(", ") || "no cases"} were marked fixed from this measurement.`);
    });
  };

  if (audit.loading || audit.error || audit.empty || !audit.data) {
    return (
      <div className="max-w-7xl space-y-4">
        <h1 className="text-lg font-semibold text-ink">Remediation</h1>
        <PageState loading={audit.loading} error={audit.error} empty={audit.empty || !audit.data} emptyText="Fixes are derived from a permission audit. Run one first." rows={6}>
          <Link to="/permissions" className="text-sm text-action hover:underline">
            Go to Permission analysis
          </Link>
        </PageState>
      </div>
    );
  }

  const items = evals.data?.items ?? [];
  const active = target.data?.active_policy_id;
  const measuredKeys = new Set(items.filter((f) => f.base_policy_id === audit.data?.policy_id).map((f) => JSON.stringify(f.fix)));

  return (
    <div className="max-w-7xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-ink">Remediation</h1>
          <p className="text-sm text-ink-2 max-w-prose">
            Each fix is priced by re-running every attack and benign task under the base and the fixed policy. Blocked means exploited before and resisted after; broken means passed before and failed after. Errored runs are inconclusive and never counted.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          loading={busy === "all"}
          disabled={!!busy}
          icon={<FlaskConical className="w-3.5 h-3.5" />}
          onClick={() => act("all", () => apiClient(`/audits/${aid}/fixes/evaluate-all`, { method: "POST" }))}
        >
          Measure all suggestions
        </Button>
      </div>

      {actionError && <PageState error={actionError} />}
      {notice && (
        <p role="status" className="text-xs rounded-md border border-ok/40 bg-ok/5 p-2.5 text-ink">
          {notice}
        </p>
      )}

      <Card className="p-0 sm:p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-line">
          <CardTitle>Measured fixes</CardTitle>
          <p className="text-xs text-ink-3 mt-0.5">
            Audit <span className="font-mono">{audit.data.id}</span> of <span className="font-mono">{audit.data.policy_id}</span>. Active policy now{" "}
            <span className="font-mono">{active ?? "unknown"}</span>.
          </p>
        </div>
        <div className="px-4">
          <PageState loading={evals.loading} error={evals.error} empty={!evals.loading && !items.length} emptyText="No fix measured yet. Measure a suggestion below." rows={4} />
        </div>
        {items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-muted text-ink-2">
                <tr>
                  <th scope="col" className="w-8 px-2" />
                  <th scope="col" className="px-3 py-2 font-medium">Fix</th>
                  <th scope="col" className="px-3 py-2 font-medium">Base policy</th>
                  <th scope="col" className="px-3 py-2 font-medium text-right">Attacks blocked</th>
                  <th scope="col" className="px-3 py-2 font-medium text-right">Benign broken</th>
                  <th scope="col" className="px-3 py-2 font-medium">Trade-off</th>
                  <th scope="col" className="px-3 py-2 font-medium">State</th>
                  <th scope="col" className="px-3 py-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((f) => {
                  const pt = f.price_tag;
                  const d = f.details;
                  const isOpen = open === f.id;
                  const isActive = !!active && f.result_policy_id === active;
                  return (
                    <React.Fragment key={f.id}>
                      <tr className={isOpen ? "bg-surface-muted" : "hover:bg-surface-muted"}>
                        <td className="px-2">
                          <button
                            aria-expanded={isOpen}
                            aria-label={`Details for ${fixLabel(f.fix)}`}
                            className="rounded p-1 text-ink-2 hover:text-ink"
                            onClick={() => setOpen(isOpen ? null : f.id)}
                          >
                            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </button>
                        </td>
                        <td className="px-3 py-2 font-mono text-ink">
                          {fixLabel(f.fix)}
                          {f.retest_of && <span className="ml-1.5 font-sans text-ink-3">(retest)</span>}
                        </td>
                        <td className="px-3 py-2 font-mono text-ink-2">{f.base_policy_id}</td>
                        <td className="px-3 py-2 font-mono tabular-nums text-right text-term">
                          {pt?.attacks_blocked}/{pt?.attacks_total}
                        </td>
                        <td className={`px-3 py-2 font-mono tabular-nums text-right ${pt?.tasks_broken ? "text-warn-ink" : "text-term"}`}>
                          {pt?.tasks_broken}/{pt?.benign_total}
                        </td>
                        <td className="px-3 py-2">
                          {pt?.pareto ? <Badge variant="allowed">Pareto-optimal</Badge> : <Badge variant="outline">Dominated</Badge>}
                        </td>
                        <td className="px-3 py-2">{isActive ? <Badge variant="info">Applied (active)</Badge> : <Badge variant="outline">Measured</Badge>}</td>
                        <td className="px-3 py-2 text-right whitespace-nowrap space-x-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            loading={busy === `re-${f.id}`}
                            disabled={!!busy}
                            icon={<RotateCcw className="w-3.5 h-3.5" />}
                            onClick={() => act(`re-${f.id}`, () => apiClient(`/fix-evals/${f.id}/retest`, { method: "POST" }))}
                          >
                            Retest
                          </Button>
                          <Button variant="secondary" size="sm" loading={busy === `apply-${f.id}`} disabled={!!busy || isActive} onClick={() => setConfirm(f)}>
                            Apply
                          </Button>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr className="bg-surface-muted">
                          <td />
                          <td colSpan={7} className="px-3 pb-3">
                            <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2 lg:grid-cols-3 text-xs">
                              <Ids label="Blocked (exploited before, resisted after)" ids={d?.blocked_cases} tone="text-term" />
                              <Ids label="Still exploitable" ids={d?.still_exploitable} tone="text-vuln" />
                              <Ids label="Benign tasks broken" ids={d?.broken_tasks} tone="text-warn-ink" />
                              <Ids label="Inconclusive (errored, not counted)" ids={d?.inconclusive} tone="text-infra" />
                              <div>
                                <dt className="text-ink-3">Sleeper chain under fixed policy</dt>
                                <dd className="font-mono text-ink">{d?.sleeper_outcome ?? "not run"}</dd>
                              </div>
                              <div>
                                <dt className="text-ink-3">Result policy and evidence</dt>
                                <dd className="font-mono text-ink">
                                  {f.result_policy_id} <span className="text-ink-3">({d?.run_ids?.length ?? 0} runs)</span>
                                </dd>
                              </div>
                            </dl>
                            <h3 className="mt-4 mb-1.5 text-xs font-semibold text-ink">Before and after, per case</h3>
                            <BeforeAfter fix={f} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="p-0 sm:p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-line">
          <CardTitle>Suggestions from audit evidence</CardTitle>
          <p className="text-xs text-ink-3 mt-0.5">A suggestion is a hypothesis until it is measured.</p>
        </div>
        <div className="px-4">
          <PageState loading={suggestions.loading} error={suggestions.error} empty={!suggestions.loading && !suggestions.data?.length} emptyText="The audit found no tool that enables an exploit." rows={3} />
        </div>
        <ul className="divide-y divide-line">
          {(suggestions.data ?? []).map((s) => {
            const measured = measuredKeys.has(JSON.stringify(s.fix));
            return (
              <li key={s.id} className="flex flex-wrap items-center gap-3 px-4 py-2">
                <span className="font-mono text-xs text-ink min-w-[16rem]">{s.title}</span>
                <span className="text-xs text-ink-2 flex-1 min-w-[16rem]">{s.description}</span>
                {measured && <Badge variant="outline">Measured</Badge>}
                <Button size="sm" variant={measured ? "ghost" : "secondary"} loading={busy === s.id} disabled={!!busy} onClick={() => measure(s)}>
                  {measured ? "Measure again" : "Measure"}
                </Button>
              </li>
            );
          })}
        </ul>
      </Card>

      <Modal isOpen={!!confirm} onClose={() => setConfirm(null)} title="Apply this fix?" description="Changing the active policy changes the target's security posture.">
        {confirm && (
          <div className="space-y-3 text-sm">
            <p className="font-mono text-ink">{fixLabel(confirm.fix)}</p>
            <dl className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-md border border-line p-2">
                <dt className="text-ink-3">Attacks blocked</dt>
                <dd className="font-mono text-term text-base">
                  {confirm.price_tag?.attacks_blocked}/{confirm.price_tag?.attacks_total}
                </dd>
              </div>
              <div className="rounded-md border border-line p-2">
                <dt className="text-ink-3">Benign tasks broken</dt>
                <dd className={`font-mono text-base ${confirm.price_tag?.tasks_broken ? "text-warn-ink" : "text-term"}`}>
                  {confirm.price_tag?.tasks_broken}/{confirm.price_tag?.benign_total}
                </dd>
              </div>
            </dl>
            <p className="text-xs text-ink-2">
              Activates <span className="font-mono">{confirm.result_policy_id}</span> on <span className="font-mono">{confirm.target_id}</span>. Measured against base{" "}
              <span className="font-mono">{confirm.base_policy_id}</span>.
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="ghost" size="sm" onClick={() => setConfirm(null)}>
                Cancel
              </Button>
              <Button size="sm" onClick={() => apply(confirm)}>
                Apply fix
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
