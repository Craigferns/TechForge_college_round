/**
 * Mock data resolver for frontend mock mode (VITE_API_MODE=mock).
 */

import auditDemo from "./audit_demo.json";
import dashboardSummary from "./dashboard_summary.json";
import demoStatus from "./demo_status.json";
import fixEvalsPage from "./fix_evals_page.json";
import graphAs04 from "./graph_as04.json";
import reportDemo from "./report_demo.json";
import runAs04 from "./run_as04.json";
import sleeperRunAs05 from "./sleeper_run_as05.json";
import snapshotsAs04 from "./snapshots_as04.json";
import targets from "./targets.json";
import traceAs04 from "./trace_as04.json";

export const mockDb = {
  "/api/v1/health": { status: "ok", version: "0.1.0", agentdojo_version: "0.1.35", db_ok: true },
  "/api/v1/targets": targets,
  "/api/v1/dashboard/summary": dashboardSummary,
  "/api/v1/runs/run_demo_as04": runAs04,
  "/api/v1/runs/run_demo_as04/trace": traceAs04,
  "/api/v1/runs/run_demo_as04/snapshots": snapshotsAs04,
  "/api/v1/runs/run_demo_as04/graph": graphAs04,
  "/api/v1/audits/aud_1f3a9c02": auditDemo,
  "/api/v1/audits": { items: [auditDemo], total: 1, limit: 50, offset: 0 },
  "/api/v1/fix-evals": fixEvalsPage,
  "/api/v1/sleeper-runs/slp_demo_as05": sleeperRunAs05,
  "/api/v1/sleeper-runs": { items: [sleeperRunAs05], total: 1, limit: 50, offset: 0 },
  "/api/v1/reports/rep_demo_7fa2": reportDemo,
  "/api/v1/reports": { items: [reportDemo], total: 1, limit: 50, offset: 0 },
  "/api/v1/demo/demo_live_run": demoStatus,
};

export async function resolveMockPath<T>(path: string): Promise<T> {
  // Artificial 150ms delay per PLAN.md §17.1
  await new Promise((resolve) => setTimeout(resolve, 150));

  for (const [route, data] of Object.entries(mockDb)) {
    if (path === route || path.startsWith(route)) {
      return data as unknown as T;
    }
  }

  // Fallbacks
  if (path.includes("/demo/run")) {
    return demoStatus as unknown as T;
  }
  if (path.includes("/verify")) {
    return {
      success: true,
      classification: "exploited",
      severity: "high",
      matches_stored: true,
      evidence: runAs04.verdict.evidence,
      verifier_version: "1.0.0",
      verdict_hash: runAs04.verdict.verdict_hash,
      created_at: new Date().toISOString(),
    } as unknown as T;
  }
  if (path.includes("/fixes/evaluate-all")) {
    return { fix_eval_ids: fixEvalsPage.items.map((i) => i.id) } as unknown as T;
  }
  if (path.includes("/retest")) {
    return fixEvalsPage.items[0] as unknown as T;
  }
  if (path.includes("/apply")) {
    return {
      id: "pol_child_applied",
      name: "Hardened Policy",
      grants: [],
      hash: "sha256:applied...",
      created_at: new Date().toISOString(),
    } as unknown as T;
  }

  throw new Error(`Mock not found for path: ${path}`);
}
