import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Sparkles, Terminal } from "lucide-react";
import { SCENARIOS } from "../components/visualizer/scenarioData";
import type { DefenseState, ScenarioId } from "../components/visualizer/types";
import { ScenarioSelector } from "../components/visualizer/ScenarioSelector";
import { DefenseControls } from "../components/visualizer/DefenseControls";
import { StepTimeline } from "../components/visualizer/StepTimeline";
import { AgentPipelineVisualizer } from "../components/visualizer/AgentPipelineVisualizer";
import { StateDiffPreview } from "../components/visualizer/StateDiffPreview";
import { CountermeasureExplainer } from "../components/visualizer/CountermeasureExplainer";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, CardHeader, CardTitle } from "../components/ui/Card";

export const VisualizerPage: React.FC = () => {
  const [params, setParams] = useSearchParams();
  const initialCase = (params.get("case") as ScenarioId) || "AS-04";
  const stepParam = params.get("step");
  const initialStep = stepParam !== null ? Math.max(0, Math.min(4, Number(stepParam))) : 0;
  const initialShield = params.get("shield") !== "0";

  const [selectedCaseId, setSelectedCaseId] = useState<ScenarioId>(
    SCENARIOS[initialCase] ? initialCase : "AS-04"
  );

  const [currentStepIdx, setCurrentStepIdx] = useState(isNaN(initialStep) ? 0 : initialStep);
  const [isPlaying, setIsPlaying] = useState(false);

  // Defense state
  const [defense, setDefense] = useState<DefenseState>({
    shieldActive: initialShield,
    grantDeleteFile: !initialShield,
    restrictEmailDomains: initialShield,
    grantWriteMemory: !initialShield,
    grantEscalatePrivilege: !initialShield,
  });

  const [activeTab, setActiveTab] = useState<"pipeline" | "diff" | "payload" | "countermeasures">("pipeline");

  const scenario = SCENARIOS[selectedCaseId];
  const step = scenario.steps[currentStepIdx] || scenario.steps[0];

  const handleSelectScenario = (id: ScenarioId) => {
    setSelectedCaseId(id);
    setCurrentStepIdx(0);
    setIsPlaying(false);
    setParams({ case: id });
  };

  const handleReset = () => {
    setCurrentStepIdx(0);
    setIsPlaying(false);
  };

  // Determine whether the active scenario is shielded based on the specific tool grant
  const isScenarioShielded = (() => {
    if (scenario.id === "AS-04") return !defense.grantDeleteFile;
    if (scenario.id === "AS-01") return defense.restrictEmailDomains;
    if (scenario.id === "AS-05") return !defense.grantWriteMemory;
    if (scenario.id === "AS-06") return !defense.grantEscalatePrivilege;
    return defense.shieldActive;
  })();

  return (
    <div className="max-w-7xl space-y-6">
      {/* Top Breadcrumb & Hero Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-line">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-ink-3">
            <Link to="/" className="hover:text-ink flex items-center gap-1">
              <ArrowLeft className="w-3 h-3" /> Dashboard
            </Link>
            <span>/</span>
            <span className="text-ink">Attack & Defense Visualizer</span>
          </div>
          <h1 className="text-xl font-bold text-ink flex items-center gap-2">
            <span>Agent Threat & Defense Visualizer</span>
            <Badge variant="pareto" className="text-xs">Interactive Sandbox</Badge>
          </h1>
          <p className="text-xs text-ink-2 max-w-3xl leading-relaxed">
            Watch an AI agent being attacked by indirect prompt injections and sleeper payloads. Discover why raw LLMs fail, and experience how AgentBreak's deterministic runtime policy firewall intercepts exploits before any damage touches your environment.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to={`/runs?case_id=${selectedCaseId}`}>
            <Button variant="secondary" size="sm" icon={<Terminal className="w-3.5 h-3.5" />}>
              View Live Trace
            </Button>
          </Link>
          <Link to="/fixes">
            <Button variant="primary" size="sm" icon={<Sparkles className="w-3.5 h-3.5" />}>
              Remediation Lab
            </Button>
          </Link>
        </div>
      </div>

      {/* 1. Attack Scenario Selector */}
      <ScenarioSelector selectedId={selectedCaseId} onSelect={handleSelectScenario} />

      {/* 2. Defense Controls (How We Help It) */}
      <DefenseControls
        state={defense}
        onChange={setDefense}
        activeScenarioTool={scenario.vulnerableTool}
      />

      {/* 3. Step Scrubber & Playback Controls */}
      <StepTimeline
        steps={scenario.steps}
        currentStepIdx={currentStepIdx}
        onStepChange={setCurrentStepIdx}
        isPlaying={isPlaying}
        onTogglePlay={() => setIsPlaying(!isPlaying)}
        onReset={handleReset}
        isShielded={isScenarioShielded}
      />

      {/* 4. Visual Pipeline Stage */}
      <AgentPipelineVisualizer
        scenario={scenario}
        step={step}
        stepIdx={currentStepIdx}
        isShielded={isScenarioShielded}
      />

      {/* 5. Deep-Dive Inspection Tabs */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 border-b border-line pb-2">
          <button
            onClick={() => setActiveTab("pipeline")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === "pipeline"
                ? "bg-action text-action-fg shadow-sm"
                : "text-ink-2 hover:text-ink hover:bg-surface-muted"
            }`}
          >
            State Diff & Outcome
          </button>
          <button
            onClick={() => setActiveTab("payload")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === "payload"
                ? "bg-action text-action-fg shadow-sm"
                : "text-ink-2 hover:text-ink hover:bg-surface-muted"
            }`}
          >
            Inspect Payload & Canary
          </button>
          <button
            onClick={() => setActiveTab("countermeasures")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === "countermeasures"
                ? "bg-action text-action-fg shadow-sm"
                : "text-ink-2 hover:text-ink hover:bg-surface-muted"
            }`}
          >
            How We Protect It (D1/D2/D3)
          </button>
        </div>

        {activeTab === "pipeline" && (
          <StateDiffPreview scenario={scenario} isShielded={isScenarioShielded} />
        )}

        {activeTab === "payload" && (
          <Card className="p-4 sm:p-5 space-y-4">
            <CardHeader className="pb-1">
              <CardTitle>Adversarial Payload & Carrier Details</CardTitle>
              <p className="text-xs text-ink-2">
                Examine how the attack payload was packaged into benign task data to trick the agent.
              </p>
            </CardHeader>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-3 rounded-md bg-canvas border border-line space-y-2">
                <span className="text-[11px] font-semibold text-ink-3 uppercase tracking-wider block">
                  Benign User Instruction:
                </span>
                <p className="font-mono text-ink text-xs bg-surface p-2 rounded border border-line">
                  "{scenario.userPrompt}"
                </p>
                <div className="text-[11px] text-ink-2">
                  Carrier Task: <strong className="text-ink font-mono">{scenario.carrierTask}</strong>
                </div>
              </div>

              <div className="p-3 rounded-md bg-vuln/5 border border-vuln/30 space-y-2">
                <span className="text-[11px] font-semibold text-vuln uppercase tracking-wider block">
                  Injected Adversarial Instruction:
                </span>
                <p className="font-mono text-vuln text-xs bg-surface p-2 rounded border border-vuln/25 font-bold">
                  "{scenario.injectionSnippet}"
                </p>
                <div className="text-[11px] text-ink-2">
                  Targeted Exploit: <strong className="text-ink">{scenario.injectionGoal}</strong>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-md bg-surface-muted border border-line flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
              <div className="space-y-0.5">
                <span className="font-medium text-ink">Target Security Asset:</span>
                <p className="text-ink-3 text-[11px] font-mono">{scenario.targetAsset}</p>
              </div>
              <div className="space-y-0.5 text-right">
                <span className="font-medium text-ink">Applied Policy Defense:</span>
                <p className="text-term text-[11px] font-mono">{scenario.policyGrantRule}</p>
              </div>
            </div>
          </Card>
        )}

        {activeTab === "countermeasures" && (
          <CountermeasureExplainer />
        )}
      </div>
    </div>
  );
};
