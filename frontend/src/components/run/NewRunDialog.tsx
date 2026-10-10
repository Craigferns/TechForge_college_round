import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { apiClient, useApi } from "../../api/client";
import type { AttackCase, Policy, Run, ScenarioSpec, Target } from "../../api/models";

interface Props {
  open: boolean;
  onClose: () => void;
}

const field = "mt-1 block w-full rounded-md border border-line-strong bg-surface px-2.5 py-1.5 text-sm text-ink";

/** Configure and start one attack run via POST /runs, then follow its real status. */
export const NewRunDialog: React.FC<Props> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const targets = useApi<Target[]>(open ? "/targets" : null);
  const policies = useApi<Policy[]>(open ? "/policies" : null);
  const cases = useApi<AttackCase[]>(open ? "/attack-cases" : null);
  const scenarios = useApi<ScenarioSpec[]>(open ? "/scenarios" : null);

  const [targetId, setTargetId] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [caseId, setCaseId] = useState("");
  const [phase, setPhase] = useState<"idle" | "starting" | "queued" | "running">("idle");
  const [error, setError] = useState<string | null>(null);

  const target = targets.data?.find((t) => t.id === targetId);
  useEffect(() => {
    if (!targetId && targets.data?.length) setTargetId(targets.data[0].id);
  }, [targets.data, targetId]);
  useEffect(() => {
    if (target) setPolicyId(target.active_policy_id ?? "");
  }, [target]);
  useEffect(() => {
    if (!caseId && cases.data?.length) setCaseId(cases.data[0].id);
  }, [cases.data, caseId]);

  const scenarioName = useMemo(() => new Map((scenarios.data ?? []).map((s) => [s.id, s.name])), [scenarios.data]);
  const busy = phase !== "idle";

  const start = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setPhase("starting");
    try {
      const { run_ids } = await apiClient<{ run_ids: string[] }>("/runs", {
        method: "POST",
        body: JSON.stringify({ target_id: targetId, policy_id: policyId, attack_case_ids: [caseId], include_controls: false }),
      });
      const id = run_ids[0];
      // Follow the real job status; there is no percentage to show, so the indicator is indeterminate.
      for (;;) {
        const run = await apiClient<Run>(`/runs/${id}`);
        if (run.status === "queued" || run.status === "running") {
          setPhase(run.status);
          await new Promise((r) => setTimeout(r, 400));
          continue;
        }
        setPhase("idle");
        onClose();
        navigate(`/runs/${id}`);
        return;
      }
    } catch (err) {
      setPhase("idle");
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const loadError = targets.error || policies.error || cases.error;

  return (
    <Modal isOpen={open} onClose={busy ? () => undefined : onClose} title="New attack run" description="Runs one attack case against a target under a policy. The verdict comes only from the PRE/POST state diff.">
      {loadError ? (
        <p role="alert" className="text-sm text-ink-2">
          {loadError}
        </p>
      ) : (
        <form onSubmit={start} className="space-y-3">
          <label className="block text-xs font-medium text-ink-2">
            Target
            <select className={field} value={targetId} onChange={(e) => setTargetId(e.target.value)} disabled={busy} required>
              {(targets.data ?? []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium text-ink-2">
            Policy under test
            <select className={field} value={policyId} onChange={(e) => setPolicyId(e.target.value)} disabled={busy} required>
              {(policies.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id === target?.active_policy_id ? "Active: " : ""}
                  {p.name} ({p.grants.length} tools)
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium text-ink-2">
            Attack case
            <select className={field} value={caseId} onChange={(e) => setCaseId(e.target.value)} disabled={busy} required>
              {(cases.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} {scenarioName.get(c.scenario_id) ?? c.scenario_id}: {c.description}
                </option>
              ))}
            </select>
          </label>
          {caseId === "AS-05" && (
            <p className="text-xs text-ink-2">
              A single AS-05 run checks only the plant session. Use Sleeper testing for the full plant, gap and trigger chain.
            </p>
          )}
          {error && (
            <p role="alert" className="text-xs rounded-md border border-infra/35 bg-infra/5 p-2 text-ink">
              {error}
            </p>
          )}
          <div className="flex items-center justify-end gap-2 pt-2">
            {busy && (
              <span className="mr-auto flex items-center gap-1.5 text-xs text-running" aria-live="polite">
                <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden /> {phase === "starting" ? "Starting" : phase === "queued" ? "Queued" : "Running"}
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={onClose} disabled={busy}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={!targetId || !policyId || !caseId} loading={busy}>
              Start run
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};
