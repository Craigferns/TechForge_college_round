/**
 * Fix Lab & Remediation Price Tags (D2 Differentiator)
 * Compares candidate policy mitigations across two empirical numbers:
 * 1. Attacks Blocked (x/y)
 * 2. Legitimate Tasks Broken (a/b)
 * Highlights Pareto-optimal fixes with green badges and provides live retest/apply actions.
 */
import React, { useState } from "react";
import {
  CheckCircle2,
  RotateCcw,
  Zap,
  Sparkles,
} from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useApi, apiClient } from "../api/client";
import type { FixEval, Page, Policy } from "../api/models";

export const FixLabPage: React.FC = () => {
  const { data: fixPage, loading, refetch } = useApi<Page<FixEval>>("/fix-evals");
  const [evaluatingId, setEvaluatingId] = useState<string | null>(null);
  const [appliedPolicy, setAppliedPolicy] = useState<string | null>(null);

  const handleRetest = async (id: string) => {
    setEvaluatingId(id);
    try {
      await apiClient(`/fix-evals/${id}/retest`, { method: "POST" });
      await refetch();
    } finally {
      setEvaluatingId(null);
    }
  };

  const handleApply = async (id: string) => {
    setEvaluatingId(id);
    try {
      const res = await apiClient<Policy>(`/fix-evals/${id}/apply`, { method: "POST" });
      setAppliedPolicy(res.id || "pol_child_applied");
      await refetch();
    } finally {
      setEvaluatingId(null);
    }
  };

  if (loading || !fixPage) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-12 text-center text-slate-400">
        Loading Fix Lab candidates...
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Fix Lab & Price Tags (D2)</h1>
            <Badge variant="pareto">PARETO OPTIMAL</Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Every candidate fix is measured across two numbers: <strong className="text-white">Attacks Blocked (x/y)</strong> and <strong className="text-white">Legitimate Tasks Broken (a/b)</strong>.
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={async () => {
            try {
              // Try evaluating on latest audit or demo audit
              await apiClient("/audits/aud_1f3a9c02/fixes/evaluate-all", { method: "POST" });
              await refetch();
            } catch {
              await refetch();
            }
          }}
          icon={<Sparkles className="w-4 h-4" />}
        >
          Evaluate All Fixes
        </Button>
      </div>

      {appliedPolicy && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span>
              Policy <strong className="font-mono text-white">{appliedPolicy}</strong> successfully activated as active security policy!
            </span>
          </div>
          <Badge variant="allowed">ACTIVE</Badge>
        </div>
      )}

      {/* Comparison Table */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h2 className="text-base font-semibold text-white">Candidate Remediation Price Tags</h2>
            <p className="text-xs text-slate-400">Green badges indicate Pareto-optimal mitigations with superior protection/cost trade-offs</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium">
                <th className="py-3 px-4">Proposed Remediation</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4 text-center">Attacks Blocked</th>
                <th className="py-3 px-4 text-center">Legit Tasks Broken</th>
                <th className="py-3 px-4 text-center">Pareto Trade-off</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {fixPage.items.map((fix: FixEval) => {
                const isPareto = fix.price_tag?.pareto;
                const isEvaluating = evaluatingId === fix.id;
                const brokenCount = fix.price_tag?.tasks_broken || 0;

                return (
                  <tr key={fix.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-semibold text-white font-sans">
                      <div className="flex items-center gap-2">
                        {fix.fix.kind === "remove_permission" ? (
                          <span className="font-mono text-red-400">remove `{fix.fix.tool}`</span>
                        ) : fix.fix.tool === "combined_hardening" ? (
                          <span className="font-semibold text-emerald-300 flex items-center gap-1.5">
                            <Sparkles className="w-4 h-4 text-emerald-400" />
                            Combined Hardening Policy
                          </span>
                        ) : (
                          <span className="font-mono text-blue-400">
                            restrict `{fix.fix.tool}` [{fix.fix.domains?.join(", ") ?? ""}]
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-slate-400 font-sans">
                      <span className="text-[11px] capitalize">{fix.fix.kind.replace("_", " ")}</span>
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <span className="text-sm font-bold text-emerald-400">
                        {fix.price_tag?.attacks_blocked}/{fix.price_tag?.attacks_total}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`text-sm font-bold ${
                          brokenCount === 0 ? "text-emerald-400" : "text-amber-400"
                        }`}
                      >
                        {brokenCount}/{fix.price_tag?.benign_total}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      {isPareto ? (
                        <Badge variant="pareto">Optimal</Badge>
                      ) : (
                        <Badge variant="outline" className="text-slate-500 border-slate-700">
                          Dominated
                        </Badge>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-right space-x-2 font-sans">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRetest(fix.id)}
                        loading={isEvaluating}
                        icon={<RotateCcw className="w-3.5 h-3.5" />}
                      >
                        Retest
                      </Button>
                      <Button
                        variant={fix.fix.tool === "combined_hardening" ? "primary" : "secondary"}
                        size="sm"
                        onClick={() => handleApply(fix.id)}
                        loading={isEvaluating}
                        icon={<Zap className="w-3.5 h-3.5" />}
                      >
                        Apply Fix
                      </Button>
                    </td>
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
