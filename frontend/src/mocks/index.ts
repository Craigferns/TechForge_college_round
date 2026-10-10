/**
 * Mock mode (VITE_API_MODE=mock): fixtures RECORDED from the real API after a real demo run
 * (scripts/gen_mocks.py; validated by scripts/check_mocks.py). Any id maps to its collection's
 * fixture, so links between pages keep working. The UI labels mock mode as "not live results".
 */

import attackCases from "./attack_cases.json";
import auditDemo from "./audit_demo.json";
import auditsPage from "./audits_page.json";
import dashboardSummary from "./dashboard_summary.json";
import demoStatus from "./demo_status.json";
import findingAs04 from "./finding_as04.json";
import findingsPage from "./findings_page.json";
import fixEvalsPage from "./fix_evals_page.json";
import fixEvalDelete from "./fix_eval_remove_delete_file.json";
import fixSuggestions from "./fix_suggestions.json";
import graphAggregate from "./graph_aggregate.json";
import graphAs04 from "./graph_as04.json";
import health from "./health.json";
import meta from "./meta.json";
import policies from "./policies.json";
import policyDiff from "./policy_diff.json";
import reportDemo from "./report_demo.json";
import runAs04 from "./run_as04.json";
import runsPage from "./runs_page.json";
import scenarios from "./scenarios.json";
import sleeperRunAs05 from "./sleeper_run_as05.json";
import sleeperRuns from "./sleeper_runs.json";
import snapshotsAs04 from "./snapshots_as04.json";
import suiteAcme from "./suite_acme.json";
import targetTest from "./target_test.json";
import targets from "./targets.json";
import traceAs04 from "./trace_as04.json";
import verifyAs04 from "./verify_as04.json";

const ID = "[^/]+";
// First match wins: more specific patterns come first.
const routes: [RegExp, unknown][] = [
  [/^\/health$/, health],
  [/^\/meta$/, meta],
  [new RegExp(`^/targets/${ID}/test$`), targetTest],
  [new RegExp(`^/targets/${ID}$`), targets[0]],
  [/^\/targets$/, targets],
  [/^\/suites\/acme$/, suiteAcme],
  [/^\/scenarios$/, scenarios],
  [/^\/attack-cases$/, attackCases],
  [new RegExp(`^/policies/${ID}/diff/${ID}$`), policyDiff],
  [/^\/policies$/, policies],
  [/^\/dashboard\/summary$/, dashboardSummary],
  [new RegExp(`^/runs/${ID}/trace$`), traceAs04],
  [new RegExp(`^/runs/${ID}/snapshots$`), snapshotsAs04],
  [new RegExp(`^/runs/${ID}/graph$`), graphAs04],
  [new RegExp(`^/runs/${ID}/verify$`), verifyAs04],
  [new RegExp(`^/runs/${ID}$`), runAs04],
  [/^\/runs$/, runsPage],
  [new RegExp(`^/audits/${ID}/fixes/evaluate-all$`), { fix_eval_ids: fixEvalsPage.items.map((i) => i.id) }],
  [new RegExp(`^/audits/${ID}/fixes$`), fixSuggestions],
  [new RegExp(`^/audits/${ID}$`), auditDemo],
  [/^\/audits$/, auditsPage],
  [new RegExp(`^/fix-evals/${ID}/retest$`), fixEvalDelete],
  [new RegExp(`^/fix-evals/${ID}/apply$`), policies[policies.length - 1]],
  [new RegExp(`^/fix-evals/${ID}$`), fixEvalDelete],
  [/^\/fix-evals$/, fixEvalsPage],
  [new RegExp(`^/sleeper-runs/${ID}$`), sleeperRunAs05],
  [/^\/sleeper-runs$/, sleeperRuns],
  [new RegExp(`^/findings/${ID}$`), findingAs04],
  [/^\/findings$/, findingsPage],
  [/^\/graph$/, graphAggregate],
  [new RegExp(`^/reports/${ID}$`), reportDemo],
  [/^\/reports$/, { items: [reportDemo], total: 1, limit: 50, offset: 0 }],
  [/^\/demo\/run$/, demoStatus],
  [new RegExp(`^/demo/${ID}$`), demoStatus],
];

export async function resolveMockPath<T>(path: string): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, 150)); // PLAN §17.1 artificial latency
  const bare = path.split("?")[0].replace(/^\/api\/v1/, "");
  const hit = routes.find(([re]) => re.test(bare));
  if (!hit) throw new Error(`Mock not found for path: ${path}`);
  return hit[1] as T;
}
