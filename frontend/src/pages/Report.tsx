/**
 * Security Evidence Report
 * Renders immutable markdown evidence reports with cryptographic run signatures,
 * environment state diff evidence, and deterministic shell replay commands.
 * Supports Markdown download and print-to-PDF styles.
 */
import React from "react";
import Markdown from "react-markdown";
import {
  Download,
  Printer,
  Copy,
  Check,
} from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useApi } from "../api/client";
import type { Report } from "../api/models";

export const ReportPage: React.FC = () => {
  const { data: report, loading } = useApi<Report>("/reports/rep_demo_7fa2");
  const [copied, setCopied] = React.useState(false);

  const handleDownload = () => {
    if (!report) return;
    const blob = new Blob([report.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `agentbreak-evidence-report-${report.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading || !report) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12 text-center text-slate-400">
        Generating evidence report...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
      {/* Action Header - hidden in print mode */}
      <div className="no-print flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Security Evidence Report</h1>
            <Badge variant="allowed">REPRODUCIBLE AUDIT</Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Complete cryptographic trace snapshots and deterministic verification commands.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            icon={<Download className="w-4 h-4" />}
          >
            Download .md
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handlePrint}
            icon={<Printer className="w-4 h-4" />}
          >
            Print to PDF
          </Button>
        </div>
      </div>

      {/* Rendered Markdown Document */}
      <Card className="bg-slate-900/90 border-slate-800 p-8 sm:p-12 shadow-2xl space-y-6 text-slate-200 leading-relaxed font-sans prose prose-invert max-w-none">
        <Markdown>{report.markdown}</Markdown>

        {/* Reproducibility Signature Footer */}
        <div className="pt-8 border-t border-slate-800/80 space-y-4 text-xs font-mono text-slate-400">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span>Report ID: {report.id}</span>
            <span>Verifier Version: {String((report.meta as Record<string, unknown> | undefined)?.verifier_version ?? "1.0")}</span>
            <span>Generated: {report.created_at}</span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
            <span className="text-emerald-400">uv run python -m agentbreak.cli verify run_demo_as04</span>
            <button
              onClick={() => {
                navigator.clipboard.writeText("uv run python -m agentbreak.cli verify run_demo_as04");
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition cursor-pointer"
              title="Copy verify command"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
};
