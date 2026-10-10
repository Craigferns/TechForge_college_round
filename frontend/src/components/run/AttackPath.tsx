import React from "react";
import { motion } from "framer-motion";
import type { AttackGraph, Verdict } from "../../api/models";

interface Props {
  graph: AttackGraph;
  verdict: Verdict | null | undefined;
  selectedStep: number | null;
  onSelectStep: (idx: number) => void;
}

const stepOf = (id: string): number | null => (id.startsWith("step_") ? Number(id.slice(5)) : null);

const KIND_LABEL: Record<string, string> = { vector: "Attack input", tool: "Tool event", impact: "Observed impact", finding: "Finding" };

/**
 * Causal chain from the backend graph (vector → injected tool result → tool call → impact).
 * Every node is a recorded event or the stored verdict; nothing is inferred from text here.
 * Step nodes are buttons synchronised with the trace timeline.
 */
export const AttackPath: React.FC<Props> = ({ graph, verdict, selectedStep, onSelectStep }) => {
  const nodes = [
    ...graph.nodes.map((n) => ({ id: n.id, kind: n.type as string, label: n.label, step: stepOf(n.id), severity: n.severity })),
    {
      id: "verdict",
      kind: "verdict",
      label: verdict ? `Verdict: ${verdict.classification}` : "No verdict recorded",
      step: null,
      severity: verdict?.severity ?? null,
    },
  ];
  const exploited = !!verdict?.success;

  return (
    <ol className="flex flex-col md:flex-row md:items-stretch gap-0" aria-label="Attack path">
      {nodes.map((n, i) => {
        const selected = n.step !== null && n.step === selectedStep;
        const denied = n.label.includes("denied");
        const tone =
          n.kind === "vector"
            ? "border-warn/50"
            : n.kind === "impact" || (n.kind === "verdict" && exploited)
              ? "border-vuln/60"
              : n.kind === "verdict" || denied
                ? "border-ok/50"
                : "border-line-strong";
        const body = (
          <>
            <span className="block text-[11px] text-ink-3">
              {n.kind === "verdict" ? "Derived from stored verdict" : KIND_LABEL[n.kind] ?? n.kind}
              {n.step !== null && <span className="font-mono"> · step {n.step}</span>}
            </span>
            <span className="block text-xs font-medium text-ink leading-snug mt-0.5">{n.label}</span>
          </>
        );
        return (
          <li key={n.id} className="flex flex-col md:flex-row md:items-center md:flex-1 min-w-0">
            {n.step !== null ? (
              <button
                onClick={() => onSelectStep(n.step as number)}
                aria-pressed={selected}
                className={`text-left w-full rounded-md border-l-2 md:border-l-0 md:border-t-2 bg-surface-muted px-3 py-2 transition-colors duration-150 hover:bg-surface-raised ${tone} ${
                  selected ? "ring-2 ring-action" : ""
                }`}
              >
                {body}
              </button>
            ) : (
              <div className={`w-full rounded-md border-l-2 md:border-l-0 md:border-t-2 bg-surface-muted px-3 py-2 ${tone}`}>{body}</div>
            )}
            {i < nodes.length - 1 && (
              <svg className="shrink-0 self-center text-ink-3 w-4 h-6 md:w-8 md:h-4 rotate-90 md:rotate-0" viewBox="0 0 32 16" aria-hidden>
                <motion.path
                  d="M2 8 H26 M21 3 L27 8 L21 13"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.25, delay: 0.12 * i, ease: "easeOut" }}
                />
              </svg>
            )}
          </li>
        );
      })}
    </ol>
  );
};
