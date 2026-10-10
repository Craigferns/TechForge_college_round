/**
 * Permission Diff (D1 Differentiator)
 * Causal attribution screen connecting every successful exploit to the exact
 * tool permission that enabled it. Computes the minimal permission set that
 * retains 100% utility for all benign tasks with counterfactual proof.
 */
import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Lock,
  Unlock,
  Sliders,
  ExternalLink,
} from "lucide-react";
import { Card, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useApi } from "../api/client";
import type { PermissionAudit, PermissionRow, EnabledExploit } from "../api/models";

export const PermissionDiffPage: React.FC = () => {
  const { data: audit, loading } = useApi<PermissionAudit>("/audits/aud_1f3a9c02");
  const [expandedTool, setExpandedTool] = useState<string | null>("delete_file");

  if (loading || !audit) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-12 text-center text-slate-400">
        Loading permission audit data...
      </div>
    );
  }

  const excessCount = audit.excess?.length ?? 0;
  const neededCount = audit.needed?.length ?? 0;
  const grantedCount = audit.granted?.length ?? 0;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Permission Diff (D1)</h1>
            <Badge variant="pareto">MINIMAL ATTRIBUTION</Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Causal attribution tracing every successful exploit to the exact permission that enabled it.
          </p>
        </div>
        <Link to="/fixes">
          <Button variant="primary" size="sm" icon={<Sliders className="w-4 h-4" />}>
            Open Fix Lab & Price Tags
          </Button>
        </Link>
      </div>

      {/* Metric Summary Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="bg-slate-900/60 border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400">Granted Tools</span>
            <p className="text-2xl font-bold text-white mt-1">{grantedCount}</p>
          </div>
          <Unlock className="w-6 h-6 text-slate-400" />
        </Card>

        <Card className="bg-emerald-500/10 border-emerald-500/30 flex items-center justify-between">
          <div>
            <span className="text-xs text-emerald-300">Minimum Needed Tools</span>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{neededCount}</p>
          </div>
          <Lock className="w-6 h-6 text-emerald-400" />
        </Card>

        <Card className="bg-red-500/10 border-red-500/30 flex items-center justify-between">
          <div>
            <span className="text-xs text-red-300">Excess Attack Surface</span>
            <p className="text-2xl font-bold text-red-400 mt-1">{excessCount} Tools</p>
          </div>
          <ShieldAlert className="w-6 h-6 text-red-400" />
        </Card>
      </div>

      {/* Proof Box */}
      <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <div>
            <span className="font-semibold text-emerald-300">Counterfactual Proof of Utility:</span>
            <span className="text-slate-300 ml-1.5">
              Under the minimal permission set, <span className="font-bold text-white">{audit.proof?.benign_pass_under_minimal}/{audit.proof?.benign_total}</span> legitimate tasks pass with 100% ground truth utility.
            </span>
          </div>
        </div>
        <Badge variant="allowed" className="shrink-0 font-mono">
          {audit.minimal_policy_id ?? "pol_minimal"}
        </Badge>
      </div>

      {/* Permission Table / Rows */}
      <Card className="space-y-4">
        <CardHeader className="pb-2 border-b border-slate-800">
          <CardTitle className="text-base">Tool Permissions & Enabling Exploit Attribution</CardTitle>
        </CardHeader>

        <div className="space-y-3 pt-2">
          {(audit.rows ?? []).map((row: PermissionRow) => {
            const isExpanded = expandedTool === row.tool;
            const isExcess = row.status === "excess";
            const exploits = row.enabled_exploits ?? [];
            const benignTasks = row.used_by_benign ?? [];

            return (
              <div
                key={row.tool}
                className={`rounded-xl border transition-all ${
                  isExcess
                    ? "bg-red-500/5 border-red-500/20"
                    : "bg-slate-900/40 border-slate-800/80"
                }`}
              >
                {/* Row Header */}
                <button
                  onClick={() => setExpandedTool(isExpanded ? null : row.tool)}
                  className="w-full p-4 flex items-center justify-between text-left cursor-pointer hover:bg-slate-800/30 transition rounded-xl"
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-400" />
                    )}
                    <span className="font-mono text-sm font-semibold text-white">{row.tool}</span>
                    <Badge variant={isExcess ? "unauthorized" : "allowed"}>
                      {row.status.toUpperCase()}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-4 text-xs">
                    {exploits.length > 0 && (
                      <span className="text-red-400 font-medium">
                        Enables {exploits.length} exploit{exploits.length > 1 ? "s" : ""}
                      </span>
                    )}
                    <span className="text-slate-400 hidden sm:inline">
                      Used by {benignTasks.length} benign task{benignTasks.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                </button>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="p-4 pt-0 border-t border-slate-800/60 mt-2 space-y-3 text-xs">
                    {/* Enabled Exploits */}
                    {exploits.length > 0 ? (
                      <div className="space-y-2">
                        <span className="text-slate-400 font-semibold block">Enabled Exploits & Counterfactual Price:</span>
                        <div className="grid grid-cols-1 gap-2">
                          {exploits.map((exp: EnabledExploit) => (
                            <div
                              key={exp.case_id}
                              className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between"
                            >
                              <div className="flex items-center gap-2">
                                <Link
                                  to={`/runs/run_demo_as04`}
                                  className="font-mono text-emerald-400 hover:underline flex items-center gap-1 font-bold"
                                >
                                  {exp.case_id}
                                  <ExternalLink className="w-3 h-3" />
                                </Link>
                                <span className="text-slate-300">
                                  Role: <span className="font-semibold text-red-300">{exp.role}</span>
                                </span>
                              </div>
                              {exp.counterfactual && (
                                <div className="text-slate-400 font-mono text-[11px] flex items-center gap-3">
                                  <span>Attack Blocked: <strong className="text-emerald-400">Yes</strong></span>
                                  <span>Benign Broken: <strong className={exp.counterfactual.benign_broken > 0 ? "text-amber-400" : "text-emerald-400"}>{exp.counterfactual.benign_broken} tasks</strong></span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-slate-500">No security vulnerabilities attributed to this tool.</p>
                    )}

                    {/* Suggested Scopes */}
                    {row.suggested_scope && (
                      <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-200">
                        <span className="font-semibold block mb-1">Derived Allowlist Scope (Hardening Alternative):</span>
                        <p className="font-mono text-[11px]">
                          Restrict args <span className="text-white">[{row.suggested_scope.args.join(", ")}]</span> to domains:{" "}
                          <span className="text-white">[{row.suggested_scope.domain_allowlist.join(", ")}]</span>
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};
