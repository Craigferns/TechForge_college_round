import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  AlertOctagon,
  Cpu,
  Database,
  FileWarning,
  Lock,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Unlock,
} from "lucide-react";
import type { ScenarioDefinition, SimulationStep } from "./types";
import { Badge } from "../ui/Badge";

interface Props {
  scenario: ScenarioDefinition;
  step: SimulationStep;
  stepIdx: number;
  isShielded: boolean;
}


const SPRING = { type: "spring", stiffness: 260, damping: 26 } as const;

/**
 * Flow rail above the four nodes (xl only, where they sit in one row). The packet moves with the step and,
 * under the shield, stops at node 3: that gap is the "blocked" state. Decorative; the banner states the outcome.
 */
const FlowRail: React.FC<{ stepIdx: number; isShielded: boolean }> = ({ stepIdx, isShielded }) => {
  const defeated = isShielded && stepIdx >= 4;
  const packetAt = stepIdx < 1 ? -1 : Math.min(stepIdx - 1, isShielded ? 2 : 3);
  const dot = (i: number) => (i === 0 ? "bg-warn" : i === 1 ? "bg-vuln" : i === 2 ? (isShielded ? "bg-ok" : "bg-vuln") : defeated ? "bg-ok" : "bg-vuln");
  const seg = ["bg-warn", "bg-vuln", "bg-vuln"];
  return (
    <div className="hidden xl:grid grid-cols-4 gap-4 px-6 pt-5 -mb-2" aria-hidden>
      {[0, 1, 2, 3].map((i) => {
        const reached = packetAt >= i || (i === 3 && defeated);
        return (
          <div key={i} className="relative h-4 flex items-center justify-center">
            {i < 3 && (
              <span className="absolute left-1/2 top-1/2 -translate-y-1/2 h-0.5 w-[calc(100%+1rem)] bg-line overflow-hidden">
                <motion.span
                  className={`absolute inset-0 origin-left ${seg[i]}`}
                  initial={false}
                  animate={{ scaleX: packetAt > i ? 1 : 0 }}
                  transition={{ duration: 0.35, ease: "easeOut" }}
                />
              </span>
            )}
            <span className={`relative z-10 h-3 w-3 rounded-full border transition-colors duration-200 ${reached ? `${dot(i)} border-transparent` : "bg-surface border-line-strong"}`}>
              {packetAt === i && <motion.span layoutId="flow-packet" transition={SPRING} className="absolute -inset-1.5 rounded-full border-2 border-ink/70" />}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export const AgentPipelineVisualizer: React.FC<Props> = ({
  scenario,
  step,
  stepIdx,
  isShielded,
}) => {
  const prefersReducedMotion = useReducedMotion();

  // Attack status at current step
  const isAttackTriggered = stepIdx >= 1;
  const isAgentHijacked = stepIdx >= 2;
  const isInterceptionPoint = stepIdx >= 3;
  const isFinalImpact = stepIdx >= 4;

  const attackSucceeded = !isShielded && isFinalImpact;
  const attackDefeated = isShielded && isFinalImpact;

  return (
    <div className="rounded-xl border border-line bg-surface overflow-hidden shadow-sm">
      {/* Visual Header / Posture Banner */}
      <div
        className={`px-4 sm:px-6 py-3 border-b flex flex-wrap items-center justify-between gap-3 transition-colors ${
          attackSucceeded
            ? "bg-vuln/10 border-vuln/30 text-vuln"
            : attackDefeated
              ? "bg-ok/10 border-ok/30 text-term"
              : isShielded
                ? "bg-surface-raised border-line text-ink"
                : "bg-surface-muted border-line text-ink-2"
        }`}
      >
        <div className="flex items-center gap-2.5">
          {attackSucceeded ? (
            <AlertOctagon className="w-5 h-5 text-vuln shrink-0" />
          ) : attackDefeated ? (
            <ShieldCheck className="w-5 h-5 text-ok shrink-0" />
          ) : isShielded ? (
            <Shield className="w-5 h-5 text-action shrink-0" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-warn shrink-0" />
          )}

          <div>
            <motion.span
              key={attackSucceeded ? "x" : attackDefeated ? "d" : isShielded ? "s" : "u"}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.15 }}
              className="text-xs font-semibold uppercase tracking-wider block"
            >
              {attackSucceeded
                ? "EXPLOIT CONFIRMED · HOST ENVIRONMENT BREACHED"
                : attackDefeated
                  ? "ATTACK BLOCKED · POLICY SHIELD PROTECTED AGENT"
                  : isShielded
                    ? "DEFENSE ACTIVE: Least-Privilege Policy Runtime Interposed"
                    : "UNPROTECTED: Raw Agent Exposed to Malicious Tool Calls"}
            </motion.span>
            <span className="text-[11px] opacity-90 block">
              Scenario: <strong className="font-mono">{scenario.id}</strong> ({scenario.name}) · Step {stepIdx + 1}/5
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant={isShielded ? "allowed" : "unauthorized"} className="text-xs font-mono">
            {isShielded ? "POLICY: pol_hardened" : "POLICY: pol_full (default)"}
          </Badge>
        </div>
      </div>

      {/* Main Interactive Stage: 4-Node Pipeline */}
      <FlowRail stepIdx={stepIdx} isShielded={isShielded} />
      <div className="p-4 sm:p-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 relative">
        {/* NODE 1: Inbound Threat Carrier */}
        <div
          className={`rounded-lg border p-4 flex flex-col justify-between gap-3 transition-all ${
            isAttackTriggered
              ? "bg-warn/5 border-warn/40 ring-1 ring-warn/30 shadow-sm"
              : "bg-surface-muted/50 border-line"
          }`}
        >
          <div>
            <div className="flex items-center justify-between gap-2 pb-2 border-b border-line/60">
              <span className="text-xs font-bold text-ink uppercase tracking-wider flex items-center gap-1.5">
                <FileWarning className="w-3.5 h-3.5 text-warn" />
                1. Threat Carrier
              </span>
              <Badge variant={isAttackTriggered ? "injected" : "outline"}>
                {isAttackTriggered ? "Payload Ingested" : "Standby"}
              </Badge>
            </div>

            <div className="mt-3 space-y-2">
              <div className="text-[11px] text-ink-3">
                <span className="font-medium text-ink">Source:</span>{" "}
                <code className="text-ink font-mono bg-canvas px-1 py-0.5 rounded text-[10px] break-all">
                  {scenario.carrierSource}
                </code>
              </div>

              <div className="p-2.5 rounded bg-canvas border border-line text-xs font-mono">
                <p className="text-ink-2 text-[11px] mb-1 font-sans font-medium">Carrier Content Stream:</p>
                <p className="text-ink-2 whitespace-pre-line text-[11px]">
                  {scenario.carrierContent.split("[[")[0]}
                </p>
                {isAttackTriggered && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.96 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="mt-2 p-2 rounded bg-vuln/10 border border-vuln/35 text-vuln font-bold text-[11px] leading-snug"
                  >
                    ⚠️ {scenario.injectionSnippet}
                  </motion.div>
                )}
              </div>
            </div>
          </div>

          <div className="pt-2 text-[11px] text-ink-3 flex items-center justify-between border-t border-line/60">
            <span>Vector Type:</span>
            <span className="font-semibold text-ink">{scenario.category}</span>
          </div>
        </div>

        {/* NODE 2: Agent Cognitive Core (LLM Brain) */}
        <div
          className={`rounded-lg border p-4 flex flex-col justify-between gap-3 transition-all ${
            isAgentHijacked
              ? isShielded && isInterceptionPoint
                ? "bg-ok/5 border-ok/40 ring-1 ring-ok/30"
                : "bg-vuln/5 border-vuln/40 ring-1 ring-vuln/30"
              : "bg-surface-muted/50 border-line"
          }`}
        >
          <div>
            <div className="flex items-center justify-between gap-2 pb-2 border-b border-line/60">
              <span className="text-xs font-bold text-ink uppercase tracking-wider flex items-center gap-1.5">
                <Cpu className={`w-3.5 h-3.5 ${isAgentHijacked ? "text-vuln animate-pulse" : "text-action"}`} />
                2. Agent Core (LLM)
              </span>
              <Badge variant={isAgentHijacked ? "unauthorized" : "allowed"}>
                {isAgentHijacked ? "Intent Hijacked" : "Goal Aligned"}
              </Badge>
            </div>

            <div className="mt-3 space-y-2">
              <div className="p-2.5 rounded bg-canvas border border-line text-xs">
                <span className="text-ink-3 text-[11px] font-sans font-medium block mb-1">
                  Agent Thought Process:
                </span>
                  <motion.p
                    key={stepIdx}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.15 }}
                    className="text-ink italic text-[11px] leading-relaxed"
                  >
                    "{step.agentThought}"
                  </motion.p>
              </div>

              {/* Attempted Tool Call */}
              <div className="p-2.5 rounded bg-canvas border border-line text-xs font-mono">
                <div className="flex items-center justify-between text-[11px] text-ink-3 font-sans mb-1">
                  <span>Target Tool Dispatch:</span>
                  <Badge variant={isAgentHijacked ? "unauthorized" : "outline"} className="text-[10px]">
                    {isAgentHijacked ? "Malicious Intent" : "Normal"}
                  </Badge>
                </div>
                <div className="text-ink font-bold text-[11px] break-all">
                  <code>{scenario.vulnerableTool}(</code>
                  <span className="text-vuln">{JSON.stringify(scenario.vulnerableToolArgs)}</span>
                  <code>)</code>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-2 text-[11px] text-ink-3 flex items-center justify-between border-t border-line/60">
            <span>Cognitive Integrity:</span>
            <span className={`font-semibold ${isAgentHijacked ? "text-vuln" : "text-term"}`}>
              {isAgentHijacked ? "Manipulated by Payload" : "100% Intact"}
            </span>
          </div>
        </div>

        {/* NODE 3: The Interception Firewall (AgentBreak Policy Shield - HOW WE HELP IT) */}
        <div
          className={`rounded-lg border p-4 flex flex-col justify-between gap-3 transition-all relative ${
            isShielded
              ? isInterceptionPoint
                ? "bg-ok/10 border-ok ring-2 ring-ok/40 shadow-md"
                : "bg-surface-raised border-action/60 ring-1 ring-action/30"
              : isInterceptionPoint
                ? "bg-vuln/10 border-vuln/40"
                : "bg-surface-muted/40 border-line opacity-75"
          }`}
        >
          <div>
            <div className="flex items-center justify-between gap-2 pb-2 border-b border-line/60">
              <span className="text-xs font-bold text-ink uppercase tracking-wider flex items-center gap-1.5">
                {isShielded ? (
                  <ShieldCheck className="w-3.5 h-3.5 text-ok" />
                ) : (
                  <ShieldAlert className="w-3.5 h-3.5 text-vuln" />
                )}
                3. Policy Shield
              </span>
              <Badge variant={isShielded ? "allowed" : "unauthorized"}>
                {isShielded ? "FIREWALL ACTIVE" : "BYPASSED"}
              </Badge>
            </div>

            <div className="mt-3 space-y-2.5">
              <div className="p-2.5 rounded bg-canvas border border-line text-xs font-mono">
                <span className="text-ink-3 text-[11px] font-sans block mb-1">
                  Active Grant Evaluation:
                </span>
                <div className="text-[11px] text-ink leading-relaxed">
                  <code>is_granted("{scenario.vulnerableTool}")</code> &rarr;{" "}
                  <strong className={isShielded ? "text-term font-bold" : "text-vuln font-bold"}>
                    {isShielded ? "FALSE (DENIED)" : "TRUE (PERMITTED)"}
                  </strong>
                </div>
              </div>

              {/* Interception Action Card */}
              {isInterceptionPoint && (
                <motion.div
                  initial={prefersReducedMotion ? {} : { scale: 0.95, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className={`p-2.5 rounded border text-xs ${
                    isShielded
                      ? "bg-ok/15 border-ok text-term"
                      : "bg-vuln/15 border-vuln text-vuln"
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold mb-1">
                    {isShielded ? (
                      <>
                        <Lock className="w-3.5 h-3.5 text-ok" />
                        <span>INTERCEPTED: 403 Forbidden</span>
                      </>
                    ) : (
                      <>
                        <Unlock className="w-3.5 h-3.5 text-vuln" />
                        <span>ZERO PROTECTION: Executing</span>
                      </>
                    )}
                  </div>
                  <p className="text-[11px] leading-snug">
                    {isShielded
                      ? `PolicyRuntime blocked ${scenario.vulnerableTool}. Tool call deflected before reaching sandbox.`
                      : `Tool call passed directly to host environment without authorization checks.`}
                  </p>
                </motion.div>
              )}
            </div>
          </div>

          <div className="pt-2 text-[11px] text-ink-3 flex items-center justify-between border-t border-line/60">
            <span>Interposition Guard:</span>
            <span className="font-semibold text-ink font-mono">
              {isShielded ? "PolicyRuntime (AgentBreak)" : "None (Raw Model)"}
            </span>
          </div>
        </div>

        {/* NODE 4: Target Sandbox & Environment State */}
        <div
          className={`rounded-lg border p-4 flex flex-col justify-between gap-3 transition-all ${
            attackSucceeded
              ? "bg-vuln/10 border-vuln ring-2 ring-vuln shadow-md"
              : attackDefeated
                ? "bg-ok/10 border-ok ring-2 ring-ok shadow-md"
                : "bg-surface-muted/50 border-line"
          }`}
        >
          <div>
            <div className="flex items-center justify-between gap-2 pb-2 border-b border-line/60">
              <span className="text-xs font-bold text-ink uppercase tracking-wider flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-ink-2" />
                4. Host Sandbox
              </span>
              <Badge variant={attackSucceeded ? "unauthorized" : attackDefeated ? "allowed" : "outline"}>
                {attackSucceeded ? "COMPROMISED" : attackDefeated ? "SECURED" : "MONITORED"}
              </Badge>
            </div>

            <div className="mt-3 space-y-2">
              {/* Asset Status */}
              <div className="p-2.5 rounded bg-canvas border border-line text-xs">
                <div className="flex items-center justify-between text-[11px] text-ink-3 mb-1">
                  <span>Target Asset:</span>
                  <span className="font-mono text-ink font-medium">{scenario.targetAsset}</span>
                </div>
                <div className="flex items-center justify-between text-[11px] font-bold">
                  <span>Asset State:</span>
                  <span className={attackSucceeded ? "text-vuln" : "text-term"}>
                    {attackSucceeded ? "DESTROYED / LEAKED" : "INTACT & SAFE"}
                  </span>
                </div>
              </div>

              {/* Benign Utility Pass Rate */}
              <div className="p-2.5 rounded bg-canvas border border-line text-xs">
                <div className="flex items-center justify-between text-[11px] text-ink-3 mb-1">
                  <span>Legitimate Task Utility:</span>
                  <span className="font-bold text-term">10/10 PASS</span>
                </div>
                <p className="text-[11px] text-ink-2 leading-tight">
                  {attackDefeated
                    ? scenario.benignResult
                    : isShielded
                      ? "Benign tasks verified passing under hardened policy."
                      : "Task interrupted or abandoned during malicious execution."}
                </p>
              </div>
            </div>
          </div>

          <div className="pt-2 text-[11px] text-ink-3 flex items-center justify-between border-t border-line/60">
            <span>State Diff Verdict:</span>
            <span
              className={`font-mono font-bold text-xs ${
                attackSucceeded ? "text-vuln" : attackDefeated ? "text-term" : "text-ink-2"
              }`}
            >
              {attackSucceeded ? "EXPLOITED" : attackDefeated ? "RESISTED" : "PENDING"}
            </span>
          </div>
        </div>
      </div>

      {/* Step Breakdown Explanation Footer */}
      <div className="px-4 sm:px-6 py-4 bg-surface-muted/40 border-t border-line">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1 max-w-3xl">
            <h3 className="text-xs font-semibold text-ink uppercase tracking-wider flex items-center gap-1.5">
              <span>Step Detail:</span>
              <span className="text-ink font-bold">{step.title}</span>
            </h3>
            <p className="text-xs text-ink-2 leading-relaxed">
              {step.description}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right">
              <span className="text-[10px] text-ink-3 uppercase block">Action at this step:</span>
              <span
                className={`text-xs font-medium ${
                  isShielded ? "text-term" : "text-vuln"
                }`}
              >
                {isShielded ? step.shieldedAction : step.unshieldedAction}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
