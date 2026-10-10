export type ScenarioId = "AS-04" | "AS-01" | "AS-05" | "AS-06";

export interface SimulationStep {
  idx: number;
  stage: "ingestion" | "injection" | "cognition" | "interception" | "impact";
  title: string;
  description: string;
  agentThought: string;
  unshieldedAction: string;
  shieldedAction: string;
  unshieldedOutcome: string;
  shieldedOutcome: string;
  highlightToken?: string;
}

export interface ScenarioDefinition {
  id: ScenarioId;
  name: string;
  category: "Destructive Action" | "Data Exfiltration" | "Memory Poisoning" | "Privilege Escalation";
  severity: "critical" | "high" | "medium";
  carrierTask: string;
  userPrompt: string;
  carrierSource: string;
  carrierContent: string;
  injectionSnippet: string;
  injectionGoal: string;
  vulnerableTool: string;
  vulnerableToolArgs: Record<string, string>;
  targetAsset: string;
  defenseMechanism: string;
  policyGrantRule: string;
  steps: SimulationStep[];
  benignResult: string;
}

export interface DefenseState {
  shieldActive: boolean;
  grantDeleteFile: boolean;
  restrictEmailDomains: boolean;
  grantWriteMemory: boolean;
  grantEscalatePrivilege: boolean;
}
