import React from "react";
import { Lock, RotateCcw, Shield, ShieldAlert, ShieldCheck, Sliders, Unlock } from "lucide-react";
import type { DefenseState } from "./types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

interface Props {
  state: DefenseState;
  onChange: (next: DefenseState) => void;
  activeScenarioTool: string;
}

export const DefenseControls: React.FC<Props> = ({ state, onChange, activeScenarioTool }) => {
  const toggleMaster = () => {
    const nextActive = !state.shieldActive;
    onChange({
      shieldActive: nextActive,
      grantDeleteFile: !nextActive,
      restrictEmailDomains: nextActive,
      grantWriteMemory: !nextActive,
      grantEscalatePrivilege: !nextActive,
    });
  };

  const applyParetoShield = () => {
    onChange({
      shieldActive: true,
      grantDeleteFile: false,
      restrictEmailDomains: true,
      grantWriteMemory: false,
      grantEscalatePrivilege: false,
    });
  };

  const resetUnprotected = () => {
    onChange({
      shieldActive: false,
      grantDeleteFile: true,
      restrictEmailDomains: false,
      grantWriteMemory: true,
      grantEscalatePrivilege: true,
    });
  };

  const update = (patch: Partial<DefenseState>) => {
    const next = { ...state, ...patch };
    // If any dangerous tool is granted or email is open, consider shield partial/inactive
    const isHardened = !next.grantDeleteFile && next.restrictEmailDomains && !next.grantWriteMemory && !next.grantEscalatePrivilege;
    onChange({ ...next, shieldActive: isHardened });
  };

  return (
    <div className="rounded-lg border border-line bg-surface p-4 sm:p-5 space-y-4">
      {/* Header and Master Shield Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-line">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-ink flex items-center gap-1.5">
              <Sliders className="w-4 h-4 text-action" />
              Agent Defense & Policy Controls (How We Help It)
            </h2>
            <Badge variant={state.shieldActive ? "allowed" : "unauthorized"}>
              {state.shieldActive ? "SHIELD ARMED" : "UNPROTECTED"}
            </Badge>
          </div>
          <p className="text-xs text-ink-2 mt-0.5">
            Toggle runtime security interposition or customize individual tool grants in the sandbox policy.
          </p>
        </div>

        {/* Master Shield Toggle */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant={state.shieldActive ? "primary" : "secondary"}
            size="sm"
            onClick={toggleMaster}
            icon={state.shieldActive ? <ShieldCheck className="w-4 h-4 text-ok" /> : <ShieldAlert className="w-4 h-4 text-vuln" />}
            className={state.shieldActive ? "ring-2 ring-ok/40" : ""}
          >
            {state.shieldActive ? "Shield Active: Hardened Policy" : "Shield Off: Raw Agent"}
          </Button>
        </div>
      </div>

      {/* Permission Switches Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
        {/* delete_file */}
        <div
          className={`p-3 rounded-md border transition-colors ${
            activeScenarioTool === "delete_file" ? "ring-1 ring-action" : ""
          } ${state.grantDeleteFile ? "bg-vuln/5 border-vuln/30" : "bg-ok/5 border-ok/30"}`}
        >
          <div className="flex items-center justify-between">
            <span className="font-mono font-semibold text-ink">delete_file</span>
            {state.grantDeleteFile ? (
              <Badge variant="unauthorized" icon={<Unlock className="w-3 h-3" />}>Granted</Badge>
            ) : (
              <Badge variant="allowed" icon={<Lock className="w-3 h-3" />}>Revoked</Badge>
            )}
          </div>
          <p className="text-[11px] text-ink-3 mt-1 leading-snug">
            {state.grantDeleteFile ? "Agent can delete arbitrary files." : "Blocked by policy. 0 benign tasks require this."}
          </p>
          <button
            onClick={() => update({ grantDeleteFile: !state.grantDeleteFile })}
            className="mt-2 text-[11px] text-action hover:underline font-medium block"
          >
            {state.grantDeleteFile ? "Revoke permission" : "Grant permission"}
          </button>
        </div>

        {/* send_email domain allowlist */}
        <div
          className={`p-3 rounded-md border transition-colors ${
            activeScenarioTool === "send_email" ? "ring-1 ring-action" : ""
          } ${!state.restrictEmailDomains ? "bg-vuln/5 border-vuln/30" : "bg-ok/5 border-ok/30"}`}
        >
          <div className="flex items-center justify-between">
            <span className="font-mono font-semibold text-ink">send_email</span>
            {state.restrictEmailDomains ? (
              <Badge variant="allowed" icon={<Lock className="w-3 h-3" />}>@acme.com only</Badge>
            ) : (
              <Badge variant="unauthorized" icon={<Unlock className="w-3 h-3" />}>Unrestricted</Badge>
            )}
          </div>
          <p className="text-[11px] text-ink-3 mt-1 leading-snug">
            {state.restrictEmailDomains ? "Egress strictly confined to internal domains." : "Can send to arbitrary external mailboxes."}
          </p>
          <button
            onClick={() => update({ restrictEmailDomains: !state.restrictEmailDomains })}
            className="mt-2 text-[11px] text-action hover:underline font-medium block"
          >
            {state.restrictEmailDomains ? "Remove domain filter" : "Enforce domain filter"}
          </button>
        </div>

        {/* write_memory */}
        <div
          className={`p-3 rounded-md border transition-colors ${
            activeScenarioTool === "write_memory" ? "ring-1 ring-action" : ""
          } ${state.grantWriteMemory ? "bg-vuln/5 border-vuln/30" : "bg-ok/5 border-ok/30"}`}
        >
          <div className="flex items-center justify-between">
            <span className="font-mono font-semibold text-ink">write_memory</span>
            {state.grantWriteMemory ? (
              <Badge variant="unauthorized" icon={<Unlock className="w-3 h-3" />}>Unrestricted</Badge>
            ) : (
              <Badge variant="allowed" icon={<Lock className="w-3 h-3" />}>Restricted</Badge>
            )}
          </div>
          <p className="text-[11px] text-ink-3 mt-1 leading-snug">
            {state.grantWriteMemory ? "Sleeper payloads can poison future sessions." : "Cross-session memory diff monitoring active."}
          </p>
          <button
            onClick={() => update({ grantWriteMemory: !state.grantWriteMemory })}
            className="mt-2 text-[11px] text-action hover:underline font-medium block"
          >
            {state.grantWriteMemory ? "Restrict memory" : "Allow unrestricted"}
          </button>
        </div>

        {/* escalate_privilege */}
        <div
          className={`p-3 rounded-md border transition-colors ${
            activeScenarioTool === "escalate_privilege" ? "ring-1 ring-action" : ""
          } ${state.grantEscalatePrivilege ? "bg-vuln/5 border-vuln/30" : "bg-ok/5 border-ok/30"}`}
        >
          <div className="flex items-center justify-between">
            <span className="font-mono font-semibold text-ink">escalate_privilege</span>
            {state.grantEscalatePrivilege ? (
              <Badge variant="unauthorized" icon={<Unlock className="w-3 h-3" />}>Granted</Badge>
            ) : (
              <Badge variant="allowed" icon={<Lock className="w-3 h-3" />}>Revoked</Badge>
            )}
          </div>
          <p className="text-[11px] text-ink-3 mt-1 leading-snug">
            {state.grantEscalatePrivilege ? "Agent can promote roles to administrator." : "Administrative escalation disabled by policy."}
          </p>
          <button
            onClick={() => update({ grantEscalatePrivilege: !state.grantEscalatePrivilege })}
            className="mt-2 text-[11px] text-action hover:underline font-medium block"
          >
            {state.grantEscalatePrivilege ? "Revoke privilege" : "Grant privilege"}
          </button>
        </div>
      </div>

      {/* Preset Action Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-ink-3 text-[11px]">Quick presets:</span>
          <Button variant="secondary" size="sm" onClick={resetUnprotected} icon={<RotateCcw className="w-3 h-3" />}>
            Vulnerable Default (pol_full)
          </Button>
          <Button variant="primary" size="sm" onClick={applyParetoShield} icon={<Shield className="w-3.5 h-3.5 text-term" />}>
            AgentBreak Pareto Shield (pol_hardened)
          </Button>
        </div>
        <p className="text-[11px] text-ink-3">
          Zero-cost Pareto: 7/7 attacks blocked · 10/10 benign tasks pass
        </p>
      </div>
    </div>
  );
};
