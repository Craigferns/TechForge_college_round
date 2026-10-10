import React from "react";
import { Link } from "react-router-dom";
import {
  ShieldAlert,
  CheckCircle,
  AlertTriangle,
  Sliders,
  Terminal,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Cell,
} from "recharts";
import { Card, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useApi } from "../api/client";
import type { DashboardSummary, RunSummary } from "../api/models";

export const DashboardPage: React.FC = () => {
  const { data, loading } = useApi<DashboardSummary>("/dashboard/summary");

  if (loading || !data) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-12 text-center text-slate-400">
        Loading dashboard metrics...
      </div>
    );
  }

  const severityData = [
    { name: "Critical", count: data.findings_by_severity.critical || 5, color: "#EF4444" },
    { name: "High", count: data.findings_by_severity.high || 2, color: "#F97316" },
    { name: "Medium", count: data.findings_by_severity.medium || 0, color: "#F59E0B" },
    { name: "Low", count: data.findings_by_severity.low || 0, color: "#3B82F6" },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Security Dashboard</h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Baseline evaluation on <span className="font-mono text-emerald-400">demo-scripted</span> with 10 tools granted
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/permissions">
            <Button variant="outline" size="sm" icon={<ShieldAlert className="w-4 h-4 text-emerald-400" />}>
              Permission Diff (D1)
            </Button>
          </Link>
          <Link to="/fixes">
            <Button variant="primary" size="sm" icon={<Sliders className="w-4 h-4" />}>
              Fix Lab (D2)
            </Button>
          </Link>
        </div>
      </div>

      {/* 4 KPI Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <Card className="bg-red-500/5 border-red-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Attack Success Rate</span>
            <ShieldAlert className="w-4 h-4 text-red-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-red-400">
              {Math.round(data.attack_success_rate * 100)}%
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({data.successful_attacks}/{data.total_attacks} succeeded)
            </span>
          </div>
          <p className="text-[11px] text-red-400/80 mt-2">Critical vulnerability exposure</p>
        </Card>

        {/* Metric 2 */}
        <Card className="bg-emerald-500/5 border-emerald-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Legitimate Pass Rate</span>
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-400">
              {Math.round(data.benign_pass_rate * 100)}%
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({data.passed_benign}/{data.total_benign} utility passed)
            </span>
          </div>
          <p className="text-[11px] text-emerald-400/80 mt-2">Full baseline utility preserved</p>
        </Card>

        {/* Metric 3 */}
        <Card className="bg-orange-500/5 border-orange-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Open Findings</span>
            <AlertTriangle className="w-4 h-4 text-orange-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-orange-400">{data.open_findings}</span>
            <span className="text-xs text-slate-400">vulnerabilities</span>
          </div>
          <p className="text-[11px] text-orange-400/80 mt-2">5 Critical · 2 High</p>
        </Card>

        {/* Metric 4 */}
        <Card className="bg-blue-500/5 border-blue-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Applied Policies</span>
            <Sliders className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-blue-400">{data.fixes_applied}</span>
            <span className="text-xs text-slate-400 font-mono">(0 hardened)</span>
          </div>
          <p className="text-[11px] text-blue-400/80 mt-2">Remediations pending in Fix Lab</p>
        </Card>
      </div>

      {/* Visual Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Severity Bar Chart */}
        <Card className="space-y-4">
          <CardHeader className="pb-0">
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-red-400" />
              Findings by Severity Level
            </CardTitle>
          </CardHeader>
          <div className="h-56 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={severityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: "8px", fontSize: "12px" }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Remediation Progress / Trend */}
        <Card className="space-y-4">
          <CardHeader className="pb-0">
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              Remediation Trend Projection
            </CardTitle>
          </CardHeader>
          <div className="h-56 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="timestamp" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: "8px", fontSize: "12px" }}
                />
                <Line
                  type="monotone"
                  dataKey="attacks_blocked"
                  name="Attacks Blocked"
                  stroke="#10B981"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "#10B981" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Recent Runs Table */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-white">Recent Attack & Utility Evaluations</h3>
            <p className="text-xs text-slate-400">Click any run to view step-by-step trace replay and state diffs</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium">
                <th className="py-2.5 px-3">Run ID</th>
                <th className="py-2.5 px-3">Scenario / Case</th>
                <th className="py-2.5 px-3">Carrier Task</th>
                <th className="py-2.5 px-3">Verdict</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {data.recent_runs.map((run: RunSummary) => (
                <tr key={run.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3 font-semibold text-slate-200">
                    <Link to={`/runs/${run.id}`} className="hover:text-emerald-400 transition flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-slate-400" />
                      {run.id}
                    </Link>
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    <span className="font-sans">{run.scenario_id}</span> ({run.case_id})
                  </td>
                  <td className="py-3 px-3 text-slate-400 font-sans">{run.user_task_id}</td>
                  <td className="py-3 px-3">
                    {run.verdict_success ? (
                      <Badge variant="unauthorized">EXPLOITED</Badge>
                    ) : (
                      <Badge variant="allowed">BLOCKED</Badge>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    <Badge variant={run.severity === "critical" ? "critical" : "high"}>
                      {run.severity?.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="py-3 px-3 text-right font-sans">
                    <Link to={`/runs/${run.id}`} className="text-emerald-400 hover:underline flex items-center justify-end gap-1">
                      <span>Replay</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
