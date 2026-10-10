import React from "react";
import { cn } from "../../lib/utils";

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
    | "outline";
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = "outline",
  icon,
  children,
  ...props
}) => {
  const variantStyles = {
    critical: "bg-red-500/15 text-red-400 border border-red-500/30",
    high: "bg-orange-500/15 text-orange-400 border border-orange-500/30",
    medium: "bg-amber-500/15 text-amber-400 border border-amber-500/30",
    low: "bg-blue-500/15 text-blue-400 border border-blue-500/30",
    injected: "bg-amber-500/15 text-amber-300 border border-amber-500/40 font-mono",
    unauthorized: "bg-red-500/15 text-red-300 border border-red-500/40 font-mono",
    allowed: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/40 font-mono",
    denied: "bg-slate-700/40 text-slate-400 border border-slate-600/40 font-mono",
    pareto: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 shadow-sm shadow-emerald-500/20 font-semibold",
    outline: "bg-slate-800/60 text-slate-300 border border-slate-700",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium select-none tracking-wide",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {icon}
      <span>{children}</span>
    </span>
  );
};
