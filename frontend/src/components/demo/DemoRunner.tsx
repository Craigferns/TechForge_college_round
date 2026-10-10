import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Circle, Loader2, PlayCircle } from "lucide-react";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { apiClient, API_MODE } from "../../api/client";
import type { DemoStage, DemoStatus } from "../../api/models";

/**
 * Starts the backend end-to-end demo (POST /demo/run) and polls its real stage status.
 * Nothing here is simulated: every stage line is text computed by the backend from the runs it executed.
 */
export const DemoRunner: React.FC<{ onDone?: () => void; variant?: "primary" | "secondary" }> = ({ onDone, variant = "secondary" }) => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const running = status?.status === "queued" || status?.status === "running";

  const start = async () => {
    setOpen(true);
    setError(null);
    setStatus(null);
    try {
      let st = await apiClient<DemoStatus>("/demo/run", { method: "POST" });
      setStatus(st);
      while (st.status === "queued" || st.status === "running") {
        await new Promise((r) => setTimeout(r, 500));
        st = await apiClient<DemoStatus>(`/demo/${st.id}`);
        setStatus(st);
      }
      if (st.status === "error") setError(st.error ?? st.stage);
      else onDone?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const links = status?.status === "completed" ? status.links : undefined;

  return (
    <>
      <Button variant={variant} size="sm" icon={<PlayCircle className="w-3.5 h-3.5" />} onClick={start} loading={running}>
        Run full demo
      </Button>
      <Modal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="End-to-end demo on the simulated target"
        description={
          API_MODE === "mock"
            ? "Mock mode: this shows recorded fixture output, not a live run."
            : "Resets only tgt_demo_scripted, attacks it, audits permissions, prices fixes, applies the zero-cost ones and re-measures."
        }
        className="max-w-xl"
      >
        <ol className="space-y-1" aria-live="polite">
          {!status && !error && (
            <li className="flex items-center gap-2 text-xs text-ink-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden /> Starting…
            </li>
          )}
          {status?.stages.map((s: DemoStage) => (
            <li key={s.id} className={`flex gap-3 rounded-md px-2.5 py-2 ${s.status === "running" ? "bg-running/8" : ""}`}>
              <span className="mt-0.5 shrink-0" aria-hidden>
                {s.status === "completed" ? (
                  <CheckCircle2 className="w-4 h-4 text-ok" />
                ) : s.status === "running" ? (
                  <Loader2 className="w-4 h-4 text-running animate-spin" />
                ) : s.status === "error" ? (
                  <AlertTriangle className="w-4 h-4 text-infra" />
                ) : (
                  <Circle className="w-4 h-4 text-ink-3" />
                )}
              </span>
              <span className="text-xs">
                <span className={`font-medium ${s.status === "pending" ? "text-ink-3" : "text-ink"}`}>{s.name}</span>
                <span className="sr-only">, {s.status}</span>
                {s.detail && <span className="block text-ink-2 mt-0.5 leading-relaxed">{s.detail}</span>}
              </span>
            </li>
          ))}
        </ol>
        {error && (
          <p role="alert" className="mt-3 text-xs rounded-md border border-infra/35 bg-infra/5 p-2.5 text-ink">
            Demo failed: {error}
          </p>
        )}
        {links && (
          <div className="mt-4 pt-3 border-t border-line flex flex-wrap gap-2">
            {(
              [
                ["Overview", links.dashboard],
                ["AS-04 trace", links.run],
                ["Permission audit", links.audit],
                ["Remediation", links.fixlab],
                ["Sleeper chain", links.sleeper],
                ["Report", links.report],
              ] as const
            ).map(([label, href]) => (
              <Button
                key={label}
                size="sm"
                variant="secondary"
                onClick={() => {
                  setOpen(false);
                  navigate(href === "/dashboard" ? "/" : href);
                }}
              >
                {label}
              </Button>
            ))}
          </div>
        )}
      </Modal>
    </>
  );
};
