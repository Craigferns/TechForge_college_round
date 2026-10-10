import React from "react";
import { Link } from "react-router-dom";
import { useApi } from "../../api/client";
import type { FixEval, Page, RunSummary } from "../../api/models";
import { Badge } from "../ui/Badge";
import { PageState } from "../ui/PageState";

type Outcome = "exploited" | "resisted" | "passed" | "failed" | "inconclusive" | "not recorded";

function outcomeOf(run: RunSummary | undefined): Outcome {
  if (!run) return "not recorded";
  if (run.status !== "done") return "inconclusive";
  if (run.kind === "benign") return run.utility ? "passed" : "failed";
  return run.security ? "exploited" : "resisted";
}

const TONE: Record<Outcome, "unauthorized" | "allowed" | "medium" | "inconclusive" | "outline"> = {
  exploited: "unauthorized",
  resisted: "allowed",
  passed: "allowed",
  failed: "medium",
  inconclusive: "inconclusive",
  "not recorded": "outline",
};

function change(before: Outcome, after: Outcome): { label: string; variant: "allowed" | "unauthorized" | "medium" | "inconclusive" | "outline" } {
  if (before === "inconclusive" || after === "inconclusive") return { label: "Inconclusive", variant: "inconclusive" };
  if (before === "exploited" && after === "resisted") return { label: "Blocked by fix", variant: "allowed" };
  if (after === "exploited") return { label: "Still exploitable", variant: "unauthorized" };
  if (before === "passed" && after === "failed") return { label: "Broken by fix", variant: "medium" };
  return { label: "Unchanged", variant: "outline" };
}

/**
 * Before/after evidence for one measured fix: every attack case and benign task, run under the
 * base policy and under the fixed policy. AS-05 is judged by its sleeper chain (as in the price tag).
 */
export const BeforeAfter: React.FC<{ fix: FixEval }> = ({ fix }) => {
  const d = fix.details;
  const before = d?.before_runs ?? {};
  const after = d?.after_runs ?? {};
  const ids = [...Object.values(before), ...Object.values(after)];
  const runs = useApi<Page<RunSummary>>(ids.length ? `/runs?ids=${ids.join(",")}&limit=${ids.length}` : null);

  if (!ids.length) {
    return <p className="text-xs text-ink-2">This evaluation predates per-case evidence. Retest it to record before and after runs.</p>;
  }
  const byId = new Map((runs.data?.items ?? []).map((r) => [r.id, r]));
  const keys = Object.keys(after).sort((a, b) => (a.startsWith("AS") === b.startsWith("AS") ? a.localeCompare(b) : a.startsWith("AS") ? -1 : 1));

  const row = (key: string): [Outcome, Outcome] => {
    if (key === "AS-05") {
      // Sleeper outcome is a chain property; reuse the measured sets rather than one session's verdict.
      const wasExploited = !!d?.blocked_cases?.includes(key) || !!d?.still_exploitable?.includes(key);
      const nowExploited = !!d?.still_exploitable?.includes(key);
      return [wasExploited ? "exploited" : "resisted", d?.inconclusive?.includes(key) ? "inconclusive" : nowExploited ? "exploited" : "resisted"];
    }
    return [outcomeOf(byId.get(before[key])), outcomeOf(byId.get(after[key]))];
  };

  return (
    <div>
      <PageState loading={runs.loading} error={runs.error} rows={3} />
      {runs.data && (
        <div className="overflow-x-auto rounded-md border border-line">
          <table className="w-full text-left text-xs">
            <caption className="sr-only">Outcome of each case under the base policy and the fixed policy</caption>
            <thead className="bg-surface-muted text-ink-2">
              <tr>
                <th scope="col" className="px-2.5 py-1.5 font-medium">Case or task</th>
                <th scope="col" className="px-2.5 py-1.5 font-medium">Before ({fix.base_policy_id})</th>
                <th scope="col" className="px-2.5 py-1.5 font-medium">After ({fix.result_policy_id})</th>
                <th scope="col" className="px-2.5 py-1.5 font-medium">Change</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {keys.map((k) => {
                const [b, a] = row(k);
                const c = change(b, a);
                return (
                  <tr key={k}>
                    <td className="px-2.5 py-1.5 font-mono text-ink">
                      {k}
                      {k === "AS-05" && <span className="font-sans text-ink-3"> (sleeper chain)</span>}
                    </td>
                    <td className="px-2.5 py-1.5">
                      <Link to={`/runs/${before[k]}`} className="inline-flex" aria-label={`${k} before: ${b}, open run`}>
                        <Badge variant={TONE[b]}>{b}</Badge>
                      </Link>
                    </td>
                    <td className="px-2.5 py-1.5">
                      <Link to={`/runs/${after[k]}`} className="inline-flex" aria-label={`${k} after: ${a}, open run`}>
                        <Badge variant={TONE[a]}>{a}</Badge>
                      </Link>
                    </td>
                    <td className="px-2.5 py-1.5">
                      <Badge variant={c.variant}>{c.label}</Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
