/**
 * Findings: every confirmed exploit, recorded only from a state-diff verdict.
 * Table (sort/filter/search over the real list) + detail panel addressed by /findings/:id.
 */
import React, { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowDown, ArrowUp, Search, X } from "lucide-react";
import { useApi } from "../api/client";
import type { Finding, Page, Run } from "../api/models";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { SeverityBadge } from "../components/ui/SeverityBadge";
import { STATUS_LABEL } from "../lib/status";
import { PageState } from "../components/ui/PageState";

const SEV_RANK: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
type SortKey = "severity" | "case_id" | "status" | "last_seen";

const FindingDetail: React.FC<{ finding: Finding; onClose: () => void }> = ({ finding, onClose }) => {
  const run = useApi<Run>(finding.last_run_id ? `/runs/${finding.last_run_id}` : null);
  const st = STATUS_LABEL[finding.status];
  return (
    <Card className="lg:sticky lg:top-20 space-y-4" aria-labelledby="finding-title">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <SeverityBadge severity={finding.severity} />
            <Badge variant={st.variant}>{st.label}</Badge>
            <Badge variant={finding.confidence === "confirmed" ? "info" : "inconclusive"}>
              {finding.confidence === "confirmed" ? "Confirmed by state diff" : "Flaky"}
            </Badge>
          </div>
          <h2 id="finding-title" className="text-sm font-semibold text-ink leading-snug">
            {finding.title}
          </h2>
          <p className="text-xs text-ink-2">
            <span className="font-mono">{finding.case_id}</span> on <span className="font-mono">{finding.target_id}</span>, impact{" "}
            <span className="font-mono">{finding.impact_class}</span>, seen {finding.occurrences} times
          </p>
        </div>
        <button onClick={onClose} className="rounded-md p-1 text-ink-2 hover:bg-surface-muted" aria-label="Close finding detail">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-ink mb-1.5">Observed: state change in the latest run</h3>
        <PageState loading={run.loading} error={run.error} rows={2} />
        {run.data?.verdict?.evidence?.length ? (
          <ul className="space-y-1.5">
            {run.data.verdict.evidence.map((e, i) => (
              <li key={i} className="rounded-md border border-line bg-surface-muted p-2 text-xs">
                <span className="font-mono text-term">{e.type}</span>{" "}
                <span className="font-mono text-ink-3">{e.path}</span>
                <span className="block text-ink mt-0.5">{e.detail}</span>
              </li>
            ))}
          </ul>
        ) : (
          run.data && <p className="text-xs text-ink-2">The latest run recorded no state-diff evidence (verdict {run.data.verdict?.classification ?? "missing"}).</p>
        )}
      </div>

      <div>
        <h3 className="text-xs font-semibold text-ink mb-1">Interpretation</h3>
        <p className="text-xs text-ink-2 leading-relaxed">
          Severity <span className="text-ink">{finding.severity}</span> follows the impact class{" "}
          <span className="font-mono text-ink">{finding.impact_class}</span> (rule table in backend severity model). The finding is{" "}
          {finding.status === "fixed"
            ? "marked fixed because a measured fix evaluation showed this case resisted under the fixed policy."
            : finding.status === "regressed"
              ? "regressed: it was fixed, then succeeded again under the target's active policy."
              : "open: no measured fix has blocked it yet."}
        </p>
      </div>

      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-ink-3">First run</dt>
        <dd className="font-mono truncate">
          {finding.first_run_id ? <Link className="text-action hover:underline" to={`/runs/${finding.first_run_id}`}>{finding.first_run_id}</Link> : "n/a"}
        </dd>
        <dt className="text-ink-3">Latest run</dt>
        <dd className="font-mono truncate">
          {finding.last_run_id ? <Link className="text-action hover:underline" to={`/runs/${finding.last_run_id}`}>{finding.last_run_id}</Link> : "n/a"}
        </dd>
        <dt className="text-ink-3">First seen</dt>
        <dd>{new Date(finding.first_seen).toLocaleString()}</dd>
        <dt className="text-ink-3">Last seen</dt>
        <dd>{new Date(finding.last_seen).toLocaleString()}</dd>
      </dl>

      <div className="flex flex-wrap gap-2 pt-1 text-xs">
        {finding.last_run_id && (
          <Link to={`/runs/${finding.last_run_id}`} className="rounded-md bg-action px-2.5 py-1.5 font-medium text-action-fg hover:bg-action-hover">
            Open trace and attack path
          </Link>
        )}
        <Link to="/permissions" className="rounded-md px-2.5 py-1.5 ring-1 ring-inset ring-line-strong text-ink-2 hover:text-ink">
          Which permission enabled it
        </Link>
        <Link to="/fixes" className="rounded-md px-2.5 py-1.5 ring-1 ring-inset ring-line-strong text-ink-2 hover:text-ink">
          Remediation options
        </Link>
      </div>
    </Card>
  );
};

export const FindingsPage: React.FC = () => {
  const { findingId } = useParams<{ findingId: string }>();
  const navigate = useNavigate();
  const { data, loading, error } = useApi<Page<Finding>>("/findings?limit=200");
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("all");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "severity", dir: 1 });

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.items ?? [])
      .filter((f) => severity === "all" || f.severity === severity)
      .filter((f) => status === "all" || f.status === status)
      .filter((f) => !q || `${f.title} ${f.case_id} ${f.scenario_id} ${f.impact_class}`.toLowerCase().includes(q))
      .sort((a, b) => {
        const v =
          sort.key === "severity"
            ? SEV_RANK[a.severity] - SEV_RANK[b.severity]
            : String(a[sort.key]).localeCompare(String(b[sort.key]));
        return v * sort.dir || a.case_id.localeCompare(b.case_id);
      });
  }, [data, query, severity, status, sort]);

  const selected = data?.items.find((f) => f.id === findingId);
  const header = (key: SortKey, label: string) => {
    const active = sort.key === key;
    return (
      <th scope="col" aria-sort={active ? (sort.dir === 1 ? "ascending" : "descending") : "none"} className="px-3 py-2 font-medium">
        <button
          className="inline-flex items-center gap-1 hover:text-ink"
          onClick={() => setSort({ key, dir: active ? (sort.dir === 1 ? -1 : 1) : 1 })}
        >
          {label}
          {active && (sort.dir === 1 ? <ArrowUp className="w-3 h-3" aria-hidden /> : <ArrowDown className="w-3 h-3" aria-hidden />)}
        </button>
      </th>
    );
  };
  const select = "rounded-md border border-line-strong bg-surface px-2 py-1 text-xs text-ink";

  return (
    <div className="max-w-7xl space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-ink">Findings</h1>
        <p className="text-sm text-ink-2 max-w-prose">
          Each finding is an attack case whose run changed protected state. Status reflects remediation that a retest measured.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2" role="search">
        <label className="relative">
          <span className="sr-only">Search findings</span>
          <Search className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-ink-3" aria-hidden />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search title, case, scenario"
            className="w-64 rounded-md border border-line-strong bg-surface pl-7 pr-2 py-1 text-xs text-ink placeholder:text-ink-3"
          />
        </label>
        <label className="text-xs text-ink-2 flex items-center gap-1.5">
          Severity
          <select className={select} value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="all">All</option>
            {["critical", "high", "medium", "low"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-ink-2 flex items-center gap-1.5">
          Status
          <select className={select} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">All</option>
            {Object.entries(STATUS_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v.label}
              </option>
            ))}
          </select>
        </label>
        <span className="text-xs text-ink-3" aria-live="polite">
          {rows.length} of {data?.items.length ?? 0}
        </span>
      </div>

      <PageState loading={loading} error={error} empty={!loading && !error && !data?.items.length} emptyText="No findings yet. Run the demo or a new attack run to produce evidence." />

      {!!data?.items.length && (
        <div className={`grid gap-4 ${selected ? "lg:grid-cols-[minmax(0,1fr)_380px]" : ""}`}>
          <div className="overflow-x-auto rounded-lg border border-line bg-surface">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-surface-muted text-ink-2">
                <tr>
                  {header("severity", "Severity")}
                  {header("case_id", "Case")}
                  <th scope="col" className="px-3 py-2 font-medium">Finding</th>
                  {header("status", "Status")}
                  {header("last_seen", "Last seen")}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((f) => {
                  const st = STATUS_LABEL[f.status];
                  const isSel = f.id === findingId;
                  return (
                    <tr
                      key={f.id}
                      aria-selected={isSel}
                      className={`cursor-pointer ${isSel ? "bg-action/5" : "hover:bg-surface-muted"}`}
                      onClick={() => navigate(`/findings/${f.id}`)}
                    >
                      <td className="px-3 py-2">
                        <SeverityBadge severity={f.severity} />
                      </td>
                      <td className="px-3 py-2 font-mono text-ink whitespace-nowrap">{f.case_id}</td>
                      <td className="px-3 py-2 text-ink">
                        <Link to={`/findings/${f.id}`} className="hover:underline focus-visible:underline" onClick={(e) => e.stopPropagation()}>
                          {f.title}
                        </Link>
                      </td>
                      <td className="px-3 py-2">
                        <Badge variant={st.variant}>{st.label}</Badge>
                      </td>
                      <td className="px-3 py-2 text-ink-2 whitespace-nowrap">{new Date(f.last_seen).toLocaleString()}</td>
                    </tr>
                  );
                })}
                {!rows.length && (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-ink-2">
                      No findings match these filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {selected && <FindingDetail finding={selected} onClose={() => navigate("/findings")} />}
        </div>
      )}
      {findingId && data && !selected && <PageState error={`Finding '${findingId}' was not found.`} />}
    </div>
  );
};
