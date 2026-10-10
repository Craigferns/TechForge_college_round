import React from "react";
import { AlertTriangle, Inbox } from "lucide-react";

interface PageStateProps {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyText?: string;
  children?: React.ReactNode; // call to action shown with the empty state
  rows?: number; // skeleton rows while loading
}

/** Loading (skeleton) / error / empty placeholder. Returns null when none applies. */
export const PageState: React.FC<PageStateProps> = ({ loading, error, empty, emptyText, children, rows = 4 }) => {
  if (error) {
    // API/transport failures are infrastructure problems: never drawn in the vulnerability colour.
    return (
      <div role="alert" className="my-4 p-3.5 rounded-lg border border-infra/35 bg-infra/5 text-sm flex gap-3">
        <AlertTriangle className="w-4 h-4 mt-0.5 text-infra shrink-0" aria-hidden />
        <div>
          <p className="font-medium text-ink">Could not load data</p>
          <p className="text-xs text-ink-2 mt-0.5">{error}</p>
        </div>
      </div>
    );
  }
  if (loading) {
    return (
      <div aria-busy="true" aria-live="polite" className="my-4 space-y-2">
        <span className="sr-only">Loading…</span>
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="h-8 rounded-md bg-surface-muted motion-safe:animate-pulse" style={{ width: `${100 - i * 9}%` }} />
        ))}
      </div>
    );
  }
  if (empty) {
    return (
      <div className="my-4 p-6 rounded-lg border border-dashed border-line-strong text-center space-y-3">
        <Inbox className="w-5 h-5 text-ink-3 mx-auto" aria-hidden />
        <p className="text-sm text-ink-2 max-w-prose mx-auto">{emptyText ?? "Nothing here yet."}</p>
        {children}
      </div>
    );
  }
  return null;
};
