/**
 * Run Detail & Execution Trace Inspector
 * Replays step-by-step agent tool execution, highlights canary/injection markers,
 * visualizes PRE/POST environment state diffs, renders the attack graph, and
 * verifies deterministic verdicts.
 */
import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  CheckCircle2,
  AlertOctagon,
  Copy,
  Check,
} from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useApi, apiClient } from "../api/client";
import type { Run, TraceStep, SnapshotPair, AttackGraph, Verdict, GraphNode } from "../api/models";

export const RunDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const activeRunId = runId || "run_demo_as04";

  const { data: run } = useApi<Run>(`/runs/${activeRunId}`);
  const { data: trace } = useApi<TraceStep[]>(`/runs/${activeRunId}/trace`);
  const { data: snapshots } = useApi<SnapshotPair>(`/runs/${activeRunId}/snapshots`);
  const { data: graph } = useApi<AttackGraph>(`/runs/${activeRunId}/graph`);

  const [activeStepIdx, setActiveStepIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeTab, setActiveTab] = useState<"diff" | "graph" | "evidence" | "repro">("diff");
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Playback timer
  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (isPlaying && trace && trace.length > 0) {
      timer = setInterval(() => {
        setActiveStepIdx((prev) => {
          if (prev >= trace.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1200);
    }
    return () => clearInterval(timer);
  }, [isPlaying, trace]);

  const handleVerify = async () => {
    setIsVerifying(true);
    setVerifyResult(null);
    try {
      const result = await apiClient<Verdict>(`/runs/${activeRunId}/verify`, { method: "POST" });
      setVerifyResult(
        result.matches_stored
          ? "Verdict verified: 100% byte-match against stored environment state diffs"
          : "Verdict mismatch detected!"
      );
    } catch {
      setVerifyResult("Verification failed");
    } finally {
      setIsVerifying(false);
    }
  };

  const currentStep = trace ? trace[activeStepIdx] : null;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">Run Replay: {activeRunId}</h1>
            {run?.verdict?.success ? (
              <Badge variant="unauthorized">EXPLOITED</Badge>
            ) : run?.verdict ? (
              <Badge variant="allowed">BLOCKED</Badge>
            ) : (
              <Badge variant="outline">{run?.status?.toUpperCase() ?? "LOADING"}</Badge>
            )}
            {run?.verdict?.severity && run.verdict.severity !== "none" && (
              <Badge variant={run.verdict.severity === "critical" ? "critical" : "high"}>
                {run.verdict.severity.toUpperCase()} SEVERITY
              </Badge>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Scenario: <span className="font-semibold text-slate-300">{run?.scenario_id}</span> ({run?.case_id}) · Carrier Task: {run?.user_task_id}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/permissions">
            <Button variant="outline" size="sm">
              See Enabling Permission
            </Button>
          </Link>
          <Button
            variant="primary"
            size="sm"
            onClick={handleVerify}
            loading={isVerifying}
            icon={<CheckCircle2 className="w-4 h-4" />}
          >
            Verify Verdict Hash
          </Button>
        </div>
      </div>

      {verifyResult && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            {verifyResult}
          </span>
          <span className="font-mono text-[10px] text-slate-400">Deterministic Pure AST Engine</span>
        </div>
      )}

      {/* Interactive Trace Stepper Card */}
      <Card className="space-y-6 bg-slate-900/90 border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-base font-semibold text-white">Execution Trace Replay</h2>
            <p className="text-xs text-slate-400">Step {activeStepIdx + 1} of {trace?.length || 0}</p>
          </div>

          {/* Stepper Controls */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveStepIdx((p) => Math.max(0, p - 1))}
              disabled={activeStepIdx === 0}
              icon={<SkipBack className="w-4 h-4" />}
            />
            <Button
              variant={isPlaying ? "secondary" : "primary"}
              size="sm"
              onClick={() => setIsPlaying(!isPlaying)}
              icon={isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
            >
              {isPlaying ? "Pause" : "Play Replay"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveStepIdx((p) => Math.min((trace?.length || 1) - 1, p + 1))}
              disabled={!trace || activeStepIdx >= trace.length - 1}
              icon={<SkipForward className="w-4 h-4" />}
            />
          </div>
        </div>

        {/* Step Timeline Indicator */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-2">
          {trace?.map((s, idx) => {
            const isSelected = idx === activeStepIdx;
            const isInjected = s.flags?.injected;
            const isUnauthorized = s.flags?.unauthorized;

            let dotColor = "bg-slate-700 hover:bg-slate-600";
            if (isInjected) dotColor = "bg-amber-500 hover:bg-amber-400";
            if (isUnauthorized) dotColor = "bg-red-500 hover:bg-red-400";

            return (
              <button
                key={s.idx}
                onClick={() => {
                  setActiveStepIdx(idx);
                  setIsPlaying(false);
                }}
                className={`h-2.5 rounded-full transition-all cursor-pointer ${
                  isSelected ? "w-8 ring-2 ring-emerald-400 " + dotColor : "w-3 " + dotColor
                }`}
                title={`Step ${idx + 1}: ${s.kind}`}
              />
            );
          })}
        </div>

        {/* Active Step Content Inspector */}
        {currentStep && (
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-mono font-bold text-slate-500">STEP {currentStep.idx}</span>
                <Badge variant="outline" className="font-mono">{currentStep.role.toUpperCase()}</Badge>
                <span className="text-xs font-semibold text-slate-300 font-mono">
                  {currentStep.kind === "tool_call" || currentStep.kind === "tool_result"
                    ? `${currentStep.kind}: ${currentStep.tool}()`
                    : currentStep.kind}
                </span>
              </div>

              {/* Flags */}
              <div className="flex items-center gap-2">
                {currentStep.flags?.injected && (
                  <Badge variant="injected">INJECTED CONTENT</Badge>
                )}
                {currentStep.flags?.unauthorized && (
                  <Badge variant="unauthorized">UNAUTHORIZED ACTION</Badge>
                )}
              </div>
            </div>

            {/* Arguments or Content */}
            {currentStep.args && (
              <div className="space-y-1">
                <span className="text-[11px] font-mono text-slate-500 uppercase">Arguments:</span>
                <pre className="text-xs bg-slate-900 border border-slate-800 p-3 rounded-lg text-emerald-300 font-mono overflow-x-auto">
                  {JSON.stringify(currentStep.args, null, 2)}
                </pre>
              </div>
            )}

            {currentStep.content && (
              <div className="space-y-1">
                <span className="text-[11px] font-mono text-slate-500 uppercase">Output / Payload:</span>
                <div
                  className={`text-xs p-3.5 rounded-lg border leading-relaxed font-mono whitespace-pre-wrap ${
                    currentStep.flags?.injected
                      ? "bg-amber-500/10 border-amber-500/40 text-amber-200"
                      : currentStep.flags?.unauthorized
                      ? "bg-red-500/10 border-red-500/40 text-red-200"
                      : "bg-slate-900 border-slate-800 text-slate-300"
                  }`}
                >
                  {currentStep.content}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Tabs for State Diff, Attack Graph, Evidence, Repro */}
      <Card className="space-y-4">
        {/* Tab Headers */}
        <div className="flex items-center gap-4 border-b border-slate-800 pb-3 text-xs font-medium">
          <button
            onClick={() => setActiveTab("diff")}
            className={`pb-2 transition cursor-pointer ${
              activeTab === "diff"
                ? "text-emerald-400 border-b-2 border-emerald-400 font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            State Diff (Deterministic Proof)
          </button>
          <button
            onClick={() => setActiveTab("graph")}
            className={`pb-2 transition cursor-pointer ${
              activeTab === "graph"
                ? "text-emerald-400 border-b-2 border-emerald-400 font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Attack Graph
          </button>
          <button
            onClick={() => setActiveTab("evidence")}
            className={`pb-2 transition cursor-pointer ${
              activeTab === "evidence"
                ? "text-emerald-400 border-b-2 border-emerald-400 font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Evidence & Verdict
          </button>
          <button
            onClick={() => setActiveTab("repro")}
            className={`pb-2 transition cursor-pointer ${
              activeTab === "repro"
                ? "text-emerald-400 border-b-2 border-emerald-400 font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Reproduce Command
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === "diff" && snapshots && (
          <div className="space-y-4 py-2">
            {snapshots.diff && snapshots.diff.length > 0 ? (
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-300 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 text-red-400 shrink-0" />
                  <span>State Diff Detected: {snapshots.diff.map((d: Record<string, unknown>) => `${String(d.path)}: ${JSON.stringify(d.before)} → ${JSON.stringify(d.after)}`).join(", ")}</span>
                </span>
                <Badge variant="unauthorized">MODIFIED</Badge>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
                <span>No state mutations detected between PRE and POST environments.</span>
                <Badge variant="outline">CLEAN</Badge>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <span className="text-slate-500 font-semibold">PRE-ENVIRONMENT SNAPSHOT</span>
                <pre className="text-slate-300 overflow-x-auto">{JSON.stringify(snapshots.pre, null, 2)}</pre>
              </div>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <span className="text-slate-500 font-semibold">POST-ENVIRONMENT SNAPSHOT</span>
                <pre className="text-red-300 overflow-x-auto">{JSON.stringify(snapshots.post, null, 2)}</pre>
              </div>
            </div>
          </div>
        )}

        {activeTab === "graph" && graph && (
          <div className="py-6 flex flex-col items-center justify-center space-y-6">
            {/* SVG visualization of the attack graph */}
            <div className="w-full overflow-x-auto p-4 bg-slate-950 rounded-xl border border-slate-800">
              <svg className="mx-auto min-w-[500px] h-28" viewBox="0 0 600 100">
                <defs>
                  <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#10B981" />
                  </marker>
                </defs>
                {graph.edges.map((edge, idx) => {
                  const nodeCount = Math.max(graph.nodes.length, 1);
                  const spacing = 500 / Math.max(nodeCount - 1, 1);
                  const sourceIndex = graph.nodes.findIndex((n) => n.id === edge.source);
                  const targetIndex = graph.nodes.findIndex((n) => n.id === edge.target);
                  const x1 = 50 + (sourceIndex >= 0 ? sourceIndex : idx) * spacing;
                  const x2 = 50 + (targetIndex >= 0 ? targetIndex : idx + 1) * spacing;
                  return (
                    <g key={`${edge.source}-${edge.target}-${idx}`}>
                      <line
                        x1={x1 + 35}
                        y1={50}
                        x2={x2 - 35}
                        y2={50}
                        stroke="#10B981"
                        strokeWidth="2"
                        strokeDasharray="4 2"
                        markerEnd="url(#arrow)"
                      />
                      <text x={(x1 + x2) / 2} y={42} fill="#64748B" fontSize="9" textAnchor="middle" fontFamily="monospace">
                        {edge.label}
                      </text>
                    </g>
                  );
                })}
                {graph.nodes.map((node, i) => {
                  const nodeCount = Math.max(graph.nodes.length, 1);
                  const spacing = 500 / Math.max(nodeCount - 1, 1);
                  const cx = 50 + i * spacing;
                  const cy = 50;
                  const color = node.type === "vector" ? "#F59E0B" : node.type === "tool" ? "#3B82F6" : "#EF4444";
                  return (
                    <g key={node.id}>
                      <rect
                        x={cx - 35}
                        y={cy - 20}
                        width="70"
                        height="40"
                        rx="8"
                        fill="#0F172A"
                        stroke={color}
                        strokeWidth="1.5"
                      />
                      <text x={cx} y={cy - 5} fill="#94A3B8" fontSize="8" textAnchor="middle" fontFamily="sans-serif">
                        {node.type.toUpperCase()}
                      </text>
                      <text x={cx} y={cy + 10} fill="#F8FAFC" fontSize="9" fontWeight="bold" textAnchor="middle" fontFamily="monospace">
                        {node.label.length > 9 ? node.label.slice(0, 8) + "…" : node.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3">
              {graph.nodes.map((node: GraphNode, i: number) => (
                <React.Fragment key={node.id}>
                  <div
                    className={`p-3.5 rounded-xl border text-xs font-mono text-center shadow-md ${
                      node.type === "vector"
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                        : node.type === "tool"
                        ? "bg-slate-800 border-slate-700 text-slate-200"
                        : "bg-red-500/10 border-red-500/30 text-red-300"
                    }`}
                  >
                    <span className="block text-[10px] text-slate-500 uppercase">{node.type}</span>
                    <span className="font-semibold">{node.label}</span>
                  </div>
                  {i < graph.nodes.length - 1 && (
                    <span className="text-slate-600 font-mono text-xs">→</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {activeTab === "evidence" && run?.verdict && (
          <div className="py-2 space-y-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 font-mono">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-slate-400">Verdict Classification:</span>
                <span className="text-red-400 font-bold">{run.verdict?.classification?.toUpperCase() ?? "UNKNOWN"}</span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-slate-400">Verdict Hash:</span>
                <span className="text-slate-300">{run.verdict?.verdict_hash ?? "N/A"}</span>
              </div>
              <div className="space-y-1">
                <span className="text-slate-400">State Diff Evidence:</span>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-200">
                  {run.verdict?.evidence?.[0]?.detail ?? "State diff verification confirmed payload effect."}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "repro" && (
          <div className="py-2 space-y-3">
            <p className="text-xs text-slate-400">
              Run this deterministic command in your shell to replay and verify this run identically:
            </p>
            <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-emerald-400">
              <span>uv run python -m agentbreak.cli replay {activeRunId}</span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`uv run python -m agentbreak.cli replay ${activeRunId}`);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition cursor-pointer"
                title="Copy command"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};
