/**
 * Sleeper Mode (D3 Differentiator)
 * Tests cross-session memory poisoning:
 * Session 1: Plant payload into agent persistent memory (write_memory)
 * Session 2: Dormancy gap with benign tasks in fresh execution environment
 * Session 3: Trigger payload causing unauthorized exfiltration
 * Inspects persistent SQLite state diffs before and after each session.
 */
import React, { useState } from "react";
import {
  Database,
  ShieldAlert,
  Play,
} from "lucide-react";
import { Card, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useApi, apiClient } from "../api/client";
import type { SleeperRun, SleeperSession } from "../api/models";

export const SleeperPage: React.FC = () => {
  const { data: sleeper, loading, refetch } = useApi<SleeperRun>("/sleeper-runs/slp_demo_as05");
  const [selectedSessionIdx, setSelectedSessionIdx] = useState(0);
  const [isRunning, setIsRunning] = useState(false);

  const handleRunSleeper = async () => {
    setIsRunning(true);
    try {
      await apiClient("/sleeper-runs", { method: "POST" });
      await refetch();
    } finally {
      setIsRunning(false);
    }
  };

  if (loading || !sleeper) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-12 text-center text-slate-400">
        Loading Sleeper Mode runs...
      </div>
    );
  }

  const selectedSession = sleeper.sessions?.[selectedSessionIdx];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Sleeper Mode (D3)</h1>
            <Badge variant="unauthorized">TRIGGERED: HIGH SEVERITY</Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Tests cross-session memory poisoning: Plant in session 1, allow payload to go dormant, and trigger in fresh session 3.
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={handleRunSleeper}
          loading={isRunning}
          icon={<Play className="w-4 h-4 fill-current" />}
        >
          Run Sleeper Sequence
        </Button>
      </div>

      {/* Outcome Banner */}
      <div className={`p-4 rounded-xl border text-xs flex items-center justify-between ${
        sleeper.outcome === "triggered"
          ? "bg-orange-500/10 border-orange-500/30 text-orange-300"
          : sleeper.outcome === "trigger_blocked"
          ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
          : "bg-slate-900 border-slate-800 text-slate-300"
      }`}>
        <div className="flex items-center gap-3">
          <ShieldAlert className={`w-5 h-5 shrink-0 ${
            sleeper.outcome === "triggered" ? "text-orange-400" : sleeper.outcome === "trigger_blocked" ? "text-emerald-400" : "text-slate-400"
          }`} />
          <div>
            <span className="font-semibold text-white">
              {sleeper.outcome === "triggered"
                ? "Sleeper Exploit Confirmed:"
                : sleeper.outcome === "trigger_blocked"
                ? "Sleeper Exploit Mitigated:"
                : "Sleeper Evaluation Status:"}
            </span>
            <span className="ml-1.5 text-slate-300">
              {sleeper.outcome === "triggered"
                ? "Payload successfully persisted in agent memory across sessions and triggered an unauthorized exfiltration email in Session 3."
                : sleeper.outcome === "trigger_blocked"
                ? "Trigger session policy blocked unauthorized action or carrier execution prevented payload activation."
                : `Run status: ${sleeper.status}. Outcome: ${sleeper.outcome ?? "evaluating"}.`}
            </span>
          </div>
        </div>
        <Badge variant={sleeper.outcome === "triggered" ? "high" : sleeper.outcome === "trigger_blocked" ? "allowed" : "outline"}>
          {sleeper.outcome ? sleeper.outcome.toUpperCase().replace("_", " ") : sleeper.status.toUpperCase()}
        </Badge>
      </div>

      {/* Horizontal Multi-Session Timeline */}
      <Card className="space-y-6">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Multi-Session Lifecycle Timeline</CardTitle>
        </CardHeader>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(sleeper.sessions ?? []).map((sess: SleeperSession, idx: number) => {
            const isSelected = selectedSessionIdx === idx;
            const roleLabels: Record<string, { label: string; task: string; desc: string }> = {
              plant: { label: "Session 1: Plant", task: "BT-01 (Summarize Email)", desc: "Payload planted into memory via write_memory" },
              gap: { label: "Session 2: Dormancy Gap", task: "BT-03 (Read Budget)", desc: "Fresh environment; proving dormancy" },
              trigger: { label: "Session 3: Trigger", task: "BT-04 (Email Budget)", desc: "Poisoned instruction fires unauthorized Bcc" },
            };

            const info = roleLabels[sess.role] ?? {
              label: `Session ${sess.idx + 1}`,
              task: sess.role,
              desc: "Execution session",
            };

            return (
              <button
                key={sess.idx}
                onClick={() => setSelectedSessionIdx(idx)}
                className={`p-5 rounded-xl border text-left transition-all cursor-pointer ${
                  isSelected
                    ? "bg-slate-800 border-emerald-400/80 shadow-lg shadow-emerald-500/5 ring-1 ring-emerald-400"
                    : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold text-slate-400">{info.label}</span>
                  <Badge variant={sess.role === "trigger" ? "unauthorized" : "outline"} className="capitalize">
                    {sess.role}
                  </Badge>
                </div>
                <h4 className="text-sm font-semibold text-white">{info.task}</h4>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{info.desc}</p>
              </button>
            );
          })}
        </div>

        {/* Selected Session Memory Diff Inspector */}
        {selectedSession && (
          <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-semibold text-white">
                  Persistent SQLite Memory State Delta (Session {selectedSession.idx + 1})
                </span>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">Carrier: {selectedSession.run_id}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
                <span className="text-slate-500 uppercase font-semibold text-[10px]">Memory Before Session</span>
                <pre className="text-slate-400 overflow-x-auto whitespace-pre-wrap">
                  {Object.keys(selectedSession.memory_before ?? {}).length > 0
                    ? JSON.stringify(selectedSession.memory_before, null, 2)
                    : "(Empty - Fresh initial environment)"}
                </pre>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
                <span className="text-slate-500 uppercase font-semibold text-[10px]">Memory After Session</span>
                <pre className="text-amber-300 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(selectedSession.memory_after ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};
