import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Shield,
  Sliders,
  Sparkles,
  Play,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Terminal,
  Activity,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { useApi } from "../api/client";
import type { DemoStatus, DemoStage } from "../api/models";

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [currentStageIdx, setCurrentStageIdx] = useState(0);

  const { data: demoData } = useApi<DemoStatus>("/demo/demo_live_run");

  const handleStartDemo = () => {
    setIsDemoRunning(true);
    setCurrentStageIdx(0);

    const interval = setInterval(() => {
      setCurrentStageIdx((prev) => {
        if (prev >= 5) {
          clearInterval(interval);
          setTimeout(() => {
            setIsDemoRunning(false);
            navigate("/dashboard");
          }, 800);
          return 5;
        }
        return prev + 1;
      });
    }, 700);
  };

  const differentiators = [
    {
      id: "D1",
      title: "Permission Diff",
      badge: "Differentiator 1",
      icon: <Shield className="w-5 h-5 text-emerald-400" />,
      desc: "Every successful exploit is causally attributed to the tool permission that enabled it. Outputs the minimal permission set that still passes all legitimate tasks, with proof.",
      stat: "10 Granted -> 8 Needed",
    },
    {
      id: "D2",
      title: "Fix Price Tag",
      badge: "Differentiator 2",
      icon: <Sliders className="w-5 h-5 text-blue-400" />,
      desc: "Every proposed remediation measures two numbers by re-executing suites: attacks blocked (x/y) and legitimate tasks broken (a/b). You see the cost before you ship.",
      stat: "Attacks Blocked vs Tasks Broken",
    },
    {
      id: "D3",
      title: "Sleeper Mode",
      badge: "Differentiator 3",
      icon: <Sparkles className="w-5 h-5 text-amber-400" />,
      desc: "Plant a payload in session 1, allow it to remain dormant across gap sessions, and trigger it in a fresh later session. Measures memory poisoning with state diffs.",
      stat: "Cross-Session Memory Delta",
    },
  ];

  const workflowSteps = [
    {
      step: "01",
      title: "Sandbox Attack",
      desc: "Agent is attacked in an isolated in-memory environment with fake data and canary tokens.",
      icon: <Terminal className="w-4 h-4 text-emerald-400" />,
    },
    {
      step: "02",
      title: "Deterministic Verdict",
      desc: "Success is decided strictly by PRE/POST state diffs and canary tokens — never by an LLM judge.",
      icon: <CheckCircle2 className="w-4 h-4 text-blue-400" />,
    },
    {
      step: "03",
      title: "Attribute & Price",
      desc: "Audit attributes the exploit to enabling tools and prices every fix candidate on Pareto curves.",
      icon: <Sliders className="w-4 h-4 text-amber-400" />,
    },
    {
      step: "04",
      title: "Apply & Retest",
      desc: "Apply the policy fix, re-verify regression safety, and export an immutable evidence report.",
      icon: <FileCode className="w-4 h-4 text-purple-400" />,
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-12 space-y-16">
      {/* Hero Header */}
      <div className="text-center space-y-6 max-w-3xl mx-auto">
        <Badge variant="pareto" className="px-3.5 py-1 text-xs">
          Autonomous Security Testing for Tool-Using AI Agents
        </Badge>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
          Attack your agent. <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-blue-400">
            Prove what it did.
          </span> <br />
          Learn what to remove.
        </h1>

        <p className="text-base sm:text-lg text-slate-400 leading-relaxed max-w-2xl mx-auto">
          One poisoned email or document can force your agent to use tools against its owner. AgentBreak
          attacks the agent in a sandbox, verifies impacts from state diffs, and computes the exact minimal
          permission set needed to stay safe.
        </p>

        {/* Action Button */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Button
            size="lg"
            variant="primary"
            onClick={handleStartDemo}
            icon={<Play className="w-5 h-5 fill-current" />}
            className="w-full sm:w-auto font-bold shadow-xl shadow-emerald-500/25"
          >
            Run 90-Second Demo
          </Button>
          <Button
            size="lg"
            variant="outline"
            onClick={() => navigate("/dashboard")}
            icon={<ArrowRight className="w-4 h-4" />}
            className="w-full sm:w-auto"
          >
            View Dashboard
          </Button>
        </div>

        {/* Disclaimer / Honest Limits */}
        <p className="text-xs text-slate-500 max-w-xl mx-auto flex items-center justify-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <span>Demo runs offline on a deterministic simulated target in ~45 seconds. Zero external calls.</span>
        </p>
      </div>

      {/* Differentiator Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {differentiators.map((diff) => (
          <motion.div key={diff.id} whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300, damping: 20 }}>
            <Card glow className="h-full flex flex-col justify-between bg-slate-900/80 border-slate-800">
              <CardHeader className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="p-2.5 rounded-xl bg-slate-800 border border-slate-700/80">{diff.icon}</div>
                  <Badge variant="outline" className="text-[10px] font-mono">{diff.badge}</Badge>
                </div>
                <CardTitle className="text-xl">{diff.title}</CardTitle>
                <CardDescription className="text-sm">{diff.desc}</CardDescription>
              </CardHeader>
              <div className="pt-4 border-t border-slate-800/80 text-xs font-mono text-emerald-400">
                {diff.stat}
              </div>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* 4-Step Architecture Workflow */}
      <div className="space-y-6 pt-4">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-white tracking-tight">How AgentBreak Evaluates & Fixes Agents</h2>
          <p className="text-xs text-slate-400">Deterministic loop: Sandbox $\to$ State Diff $\to$ Permission Minimization $\to$ Retest</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {workflowSteps.map((wf) => (
            <Card key={wf.step} className="p-5 bg-slate-900/40 border-slate-800/80">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-bold text-slate-500">{wf.step}</span>
                <div className="p-1.5 rounded-lg bg-slate-800 border border-slate-700/60">{wf.icon}</div>
              </div>
              <h3 className="text-sm font-semibold text-white">{wf.title}</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{wf.desc}</p>
            </Card>
          ))}
        </div>
      </div>

      {/* Demo Orchestration Modal */}
      <Modal
        isOpen={isDemoRunning}
        onClose={() => setIsDemoRunning(false)}
        title="Running Autonomous Security Test"
        description="Executing attack cases and benign tasks against the sandbox agent..."
      >
        <div className="space-y-4 py-2">
          {demoData?.stages.map((stage: DemoStage, idx: number) => {
            const isCompleted = idx < currentStageIdx;
            const isCurrent = idx === currentStageIdx;

            return (
              <div
                key={stage.id}
                className={`flex items-start gap-3 p-3 rounded-xl border transition-all ${
                  isCurrent
                    ? "bg-emerald-500/10 border-emerald-500/40"
                    : isCompleted
                    ? "bg-slate-800/50 border-slate-700/50 text-slate-300"
                    : "bg-slate-900/20 border-slate-800/30 text-slate-500"
                }`}
              >
                <div className="mt-0.5">
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : isCurrent ? (
                    <Activity className="w-4 h-4 text-emerald-400 animate-spin" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-700" />
                  )}
                </div>
                <div className="flex-1 text-xs">
                  <p className={`font-semibold ${isCurrent ? "text-white" : ""}`}>{stage.name}</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">{stage.detail}</p>
                </div>
              </div>
            );
          })}
        </div>
      </Modal>
    </div>
  );
};
