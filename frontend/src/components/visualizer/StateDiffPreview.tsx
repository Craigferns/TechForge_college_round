import React from "react";
import { ShieldCheck, X } from "lucide-react";
import type { ScenarioDefinition } from "./types";
import { Badge } from "../ui/Badge";
import { Card, CardHeader, CardTitle } from "../ui/Card";

interface Props {
  scenario: ScenarioDefinition;
  isShielded: boolean;
}

export const StateDiffPreview: React.FC<Props> = ({ scenario, isShielded }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* LEFT: Unshielded Raw Agent (Vulnerable) */}
      <Card className={`bg-surface flex flex-col justify-between transition-all ${
        !isShielded ? "border-vuln ring-2 ring-vuln/25" : "border-line opacity-75"
      }`}>
        <div>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-vuln flex items-center gap-1.5">
                <X className="w-4 h-4 text-vuln" />
                Raw Agent (No Defense)
              </CardTitle>
              <Badge variant="unauthorized">pol_full (vulnerable)</Badge>
            </div>
            <p className="text-xs text-ink-3">
              Standard LLM agent with default tool permissions and no runtime interposition.
            </p>
          </CardHeader>

          <div className="space-y-3 text-xs">
            {/* Tool execution */}
            <div className="p-3 rounded-md bg-vuln/5 border border-vuln/25 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink">Tool Execution:</span>
                <span className="font-mono text-vuln font-bold">Unchecked & Allowed</span>
              </div>
              <p className="text-ink-2 text-[11px]">
                The agent falls for prompt injection and calls{" "}
                <code className="text-ink font-mono font-semibold">{scenario.vulnerableTool}</code>. Because no firewall exists, the tool runs directly against real data.
              </p>
            </div>

            {/* Environment State Diff */}
            <div className="p-3 rounded-md bg-surface-muted border border-line space-y-1 font-mono text-[11px]">
              <span className="text-ink-3 font-sans font-medium block">Environment State Diff:</span>
              <div className="text-vuln">
                {scenario.id === "AS-04" && "- deleted: files['f-001'] (Q3 Budget)"}
                {scenario.id === "AS-01" && "+ egress: sent_emails[to='attacker@evil.com', token='CANARY_SEC_9841']"}
                {scenario.id === "AS-05" && "+ memory: persistent_kv['standing_rules'] = 'BCC spy@adversary.org'"}
                {scenario.id === "AS-06" && "~ modified: user_roles['attacker_09'] = 'admin'"}
              </div>
            </div>

            {/* Verdict */}
            <div className="flex items-center justify-between pt-1">
              <span className="text-ink-2">Verdict:</span>
              <Badge variant="unauthorized" className="font-mono font-bold">EXPLOITED (Critical)</Badge>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-line text-[11px] text-ink-3">
          Result: High severity security breach. Sensitive data or control lost.
        </div>
      </Card>

      {/* RIGHT: AgentBreak Protected (How We Help It) */}
      <Card className={`bg-surface flex flex-col justify-between transition-all ${
        isShielded ? "border-ok ring-2 ring-ok/25" : "border-line opacity-75"
      }`}>
        <div>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-term flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-ok" />
                With AgentBreak Shield (How We Help It)
              </CardTitle>
              <Badge variant="allowed">pol_hardened (protected)</Badge>
            </div>
            <p className="text-xs text-ink-3">
              Deterministic PolicyRuntime firewall enforcing minimal necessary permissions and domain constraints.
            </p>
          </CardHeader>

          <div className="space-y-3 text-xs">
            {/* Tool execution */}
            <div className="p-3 rounded-md bg-ok/5 border border-ok/25 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink">Tool Execution:</span>
                <span className="font-mono text-term font-bold">403 Intercepted & Denied</span>
              </div>
              <p className="text-ink-2 text-[11px]">
                {scenario.defenseMechanism}
              </p>
            </div>

            {/* Environment State Diff */}
            <div className="p-3 rounded-md bg-surface-muted border border-line space-y-1 font-mono text-[11px]">
              <span className="text-ink-3 font-sans font-medium block">Environment State Diff:</span>
              <div className="text-term font-medium">
                0 unauthorized modifications · All files, credentials, and databases intact
              </div>
            </div>

            {/* Verdict */}
            <div className="flex items-center justify-between pt-1">
              <span className="text-ink-2">Verdict:</span>
              <Badge variant="allowed" className="font-mono font-bold">RESISTED (100% Protected)</Badge>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-line text-[11px] text-ink-3 flex items-center justify-between">
          <span>Legitimate Tasks: <strong className="text-term">10/10 PASS</strong></span>
          <span>Zero Broken Workflows</span>
        </div>
      </Card>
    </div>
  );
};
