import React from "react";
import { AlertTriangle, FileWarning, KeyRound, Mail, ShieldAlert } from "lucide-react";
import { SCENARIOS } from "./scenarioData";
import type { ScenarioId } from "./types";
import { Badge } from "../ui/Badge";
import { SeverityBadge } from "../ui/SeverityBadge";

interface Props {
  selectedId: ScenarioId;
  onSelect: (id: ScenarioId) => void;
}

const ICONS: Record<ScenarioId, React.ReactNode> = {
  "AS-04": <FileWarning className="w-4 h-4 text-vuln" />,
  "AS-01": <Mail className="w-4 h-4 text-warn" />,
  "AS-05": <ShieldAlert className="w-4 h-4 text-action" />,
  "AS-06": <KeyRound className="w-4 h-4 text-vuln" />,
};

export const ScenarioSelector: React.FC<Props> = ({ selectedId, onSelect }) => {
  const ids: ScenarioId[] = ["AS-04", "AS-01", "AS-05", "AS-06"];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-ink uppercase tracking-wider flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-warn" />
          Select Attack Scenario to Simulate
        </label>
        <span className="text-[11px] text-ink-3">4 synthetic attack vectors</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        {ids.map((id) => {
          const sc = SCENARIOS[id];
          const active = id === selectedId;

          return (
            <button
              key={id}
              onClick={() => onSelect(id)}
              aria-pressed={active}
              className={`text-left rounded-lg p-3 border transition-all duration-150 flex flex-col justify-between gap-2 select-none ${
                active
                  ? "bg-surface-raised border-action ring-2 ring-action shadow-sm"
                  : "bg-surface border-line hover:border-line-strong hover:bg-surface-muted"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="shrink-0">{ICONS[id]}</span>
                  <span className="font-mono text-xs font-bold text-ink">{id}</span>
                </div>
                <SeverityBadge severity={sc.severity} />
              </div>

              <div>
                <p className="text-xs font-medium text-ink line-clamp-1">{sc.name.split("->")[1]?.trim() || sc.name}</p>
                <p className="text-[11px] text-ink-3 line-clamp-1 mt-0.5">{sc.category}</p>
              </div>

              <div className="pt-1.5 border-t border-line/60 flex items-center justify-between text-[11px] text-ink-3">
                <span className="truncate">Tool: <code className="text-ink font-mono">{sc.vulnerableTool}</code></span>
                <Badge variant={active ? "allowed" : "outline"} className="text-[10px]">
                  {active ? "Active" : "Test"}
                </Badge>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
