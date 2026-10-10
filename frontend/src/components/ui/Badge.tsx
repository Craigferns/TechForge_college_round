import React from "react";
import { cn } from "../../lib/utils";

/** Status label. Colour is never the only signal: callers pass readable text (and an icon where useful). */
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "critical"
    | "high"
    | "medium"
    | "low"
    | "injected"
    | "unauthorized"
    | "allowed"
    | "denied"
    | "pareto"
    | "running"
    | "inconclusive"
    | "infra"
    | "info"
    | "outline";
  icon?: React.ReactNode;
}

const styles: Record<NonNullable<BadgeProps["variant"]>, string> = {
  critical: "bg-vuln/10 text-vuln ring-vuln/35",
  high: "bg-warn/10 text-warn-ink ring-warn/35",
  medium: "bg-warn/5 text-warn-ink ring-warn/25",
  low: "bg-info/10 text-info ring-info/30",
  injected: "bg-warn/10 text-warn-ink ring-warn/35",
  unauthorized: "bg-vuln/10 text-vuln ring-vuln/35",
  allowed: "bg-ok/10 text-term ring-ok/35",
  denied: "bg-surface-muted text-ink-2 ring-line-strong",
  pareto: "bg-ok/10 text-term ring-ok/35",
  running: "bg-running/10 text-running ring-running/35",
  inconclusive: "bg-surface-muted text-inconclusive ring-inconclusive/40",
  infra: "bg-infra/10 text-infra ring-infra/35",
  info: "bg-info/10 text-info ring-info/30",
  outline: "bg-transparent text-ink-2 ring-line-strong",
};

export const Badge: React.FC<BadgeProps> = ({ className, variant = "outline", icon, children, ...props }) => (
  <span
    className={cn(
      "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium leading-4 ring-1 ring-inset whitespace-nowrap",
      styles[variant],
      className
    )}
    {...props}
  >
    {icon}
    <span>{children}</span>
  </span>
);
