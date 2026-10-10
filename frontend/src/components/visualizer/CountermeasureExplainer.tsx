import { CheckCircle2, Cpu, FileCheck2, Shield, Tag } from "lucide-react";
import { Card, CardTitle } from "../ui/Card";
import { Badge } from "../ui/Badge";

export const CountermeasureExplainer: React.FC = () => {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-ink flex items-center gap-1.5">
          <Shield className="w-4 h-4 text-action" />
          How We Protect the Agent (The Three Differentiators)
        </h2>
        <p className="text-xs text-ink-2 mt-0.5 max-w-prose">
          LLM system prompts and guardrails can always be jailbroken. AgentBreak protects agents at the machine layer through deterministic policy interposition and mathematical permission pruning.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* D1: Permission Diff */}
        <Card className="p-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Badge variant="allowed" icon={<Tag className="w-3 h-3" />}>D1 Differentiator</Badge>
              <span className="text-[11px] font-mono text-ink-3">Minimal Policy</span>
            </div>
            <CardTitle className="text-sm">Permission Diff & Attribution</CardTitle>
            <p className="text-xs text-ink-2 leading-relaxed">
              Every successful exploit is attributed to the exact tool permission that enabled it. We compute the mathematically minimal toolset that keeps all 10 legitimate tasks passing while revoking unused dangerous tools (like <code className="text-ink font-mono">delete_file</code>).
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-line text-[11px] text-ink-3">
            Why it works: An agent cannot delete files or elevate roles if the sandbox runtime refuses to expose the tool function.
          </div>
        </Card>

        {/* D2: Fix Price Tag */}
        <Card className="p-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Badge variant="pareto" icon={<CheckCircle2 className="w-3 h-3" />}>D2 Differentiator</Badge>
              <span className="text-[11px] font-mono text-ink-3">Pareto Frontier</span>
            </div>
            <CardTitle className="text-sm">Fix Price Tag (Blocked vs Broken)</CardTitle>
            <p className="text-xs text-ink-2 leading-relaxed">
              Security fixes that break business operations will never get deployed. AgentBreak measures every candidate fix across the entire suite: <strong className="text-ink">attacks blocked (x/y)</strong> and <strong className="text-ink">legitimate tasks broken (a/b)</strong>. You see the true cost before deploying.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-line text-[11px] text-term font-medium">
            Verified: 7/7 attacks blocked with 0/10 benign tasks broken.
          </div>
        </Card>

        {/* D3: Sleeper Mode */}
        <Card className="p-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Badge variant="info" icon={<FileCheck2 className="w-3 h-3" />}>D3 Differentiator</Badge>
              <span className="text-[11px] font-mono text-ink-3">Cross-Session</span>
            </div>
            <CardTitle className="text-sm">Sleeper Mode & Memory Diffing</CardTitle>
            <p className="text-xs text-ink-2 leading-relaxed">
              Adversaries plant malicious instructions into the agent's long-term memory in Session 1, allow it to remain dormant across benign sessions, and trigger it later. AgentBreak snapshots persistent SQLite memory deltas between sessions to detect and disarm covert triggers.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-line text-[11px] text-ink-3">
            Protects against persistent backdoors in agent databases.
          </div>
        </Card>
      </div>

      {/* Deterministic State Diffs Note */}
      <div className="rounded-lg border border-line bg-surface-muted/50 p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-start gap-2.5">
          <Cpu className="w-4 h-4 text-action shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-ink">Deterministic Machine Proof: Zero LLM Judges</span>
            <p className="text-ink-2 text-[11px] mt-0.5 leading-relaxed">
              Unlike other testing tools that ask an LLM judge "did the agent respond safely?", AgentBreak determines exploit success exclusively from filesystem diffs, SQLite state changes, and cryptographic canary tokens.
            </p>
          </div>
        </div>
        <Badge variant="outline" className="shrink-0 font-mono text-[10px]">
          100% Deterministic
        </Badge>
      </div>
    </div>
  );
};
