/**
 * Security Evidence Report
 * Renders immutable markdown evidence reports with cryptographic run signatures,
 * environment state diff evidence, and deterministic shell replay commands.
 * Supports Markdown download and print-to-PDF styles.
 */
import React from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useNavigate, useParams } from "react-router-dom";
import {
  Download,
  Printer,
} from "lucide-react";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { apiClient, useByIdOrLatest } from "../api/client";
import { PageState } from "../components/ui/PageState";
import type { Report } from "../api/models";

export const ReportPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const { data: report, loading, error, empty } = useByIdOrLatest<Report>("/reports", reportId);
  const [busy, setBusy] = React.useState(false);
  const bodyRef = React.useRef<HTMLDivElement>(null);
  const [genError, setGenError] = React.useState<string | null>(null);

  // A new report snapshots the records as they are now (target's active policy).
  const generate = async () => {
    setBusy(true);
    setGenError(null);
    try {
      const target = await apiClient<{ active_policy_id: string | null }>("/targets/tgt_demo_scripted");
      const rep = await apiClient<Report>("/reports", {
        method: "POST",
        body: JSON.stringify({ target_id: "tgt_demo_scripted", policy_id: target.active_policy_id ?? "pol_full" }),
      });
      navigate(`/report/${rep.id}`);
    } catch (e) {
      setGenError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const save = (content: string, type: string, ext: string) => {
    if (!report) return;
    const url = URL.createObjectURL(new Blob([content], { type }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `agentbreak-evidence-report-${report.id}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const exportMarkdown = () => report && save(report.markdown, "text/markdown", "md");
  const exportJson = () => report && save(JSON.stringify(report, null, 2), "application/json", "json");
  // Standalone HTML from the rendered report (react-markdown never renders raw HTML, so the markup is safe).
  const exportHtml = () => {
    if (!report || !bodyRef.current) return;
    const css =
      "body{font:14px/1.6 system-ui,sans-serif;color:#0F172A;background:#F8FAFC;max-width:60rem;margin:2rem auto;padding:0 1rem}" +
      "h1{font-size:1.4rem}h2{font-size:1.1rem;border-bottom:1px solid #E2E8F0;padding-bottom:.25rem;margin-top:2rem}" +
      "code,pre{font-family:ui-monospace,monospace;font-size:.85em}pre{background:#fff;border:1px solid #E2E8F0;padding:.6rem;overflow:auto;white-space:pre-wrap}" +
      "table{border-collapse:collapse;width:100%;font-size:.8rem}th,td{border:1px solid #E2E8F0;padding:.25rem .5rem;text-align:left;vertical-align:top}th{background:#F1F5F9}";
    const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>AgentBreak report ${report.id}</title><style>${css}</style></head><body>${bodyRef.current.innerHTML}</body></html>`;
    save(html, "text/html", "html");
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading || error || empty || !report) {
    return (
      <PageState loading={loading} error={error ?? genError} empty={empty || !report} emptyText="No evidence report yet.">
        <Button variant="primary" size="sm" loading={busy} onClick={generate}>
          Generate report from current records
        </Button>
      </PageState>
    );
  }

  return (
    <div className="max-w-4xl space-y-4">
      {/* Action Header - hidden in print mode */}
      <div className="no-print flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-line">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-ink">Evidence report</h1>
          </div>
          <p className="text-xs sm:text-sm text-ink-2 mt-1">
            Built only from persisted runs, verdicts, audits and fix evaluations. Each finding lists a command that re-verifies it from stored snapshots.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" loading={busy} onClick={generate}>
            Regenerate
          </Button>
          <span className="flex items-center gap-1" role="group" aria-label="Export report">
            <Download className="w-3.5 h-3.5 text-ink-3" aria-hidden />
            <Button variant="ghost" size="sm" onClick={exportMarkdown}>
              Markdown
            </Button>
            <Button variant="ghost" size="sm" onClick={exportJson}>
              JSON
            </Button>
            <Button variant="ghost" size="sm" onClick={exportHtml}>
              HTML
            </Button>
          </span>
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
      <Card className="p-4 sm:p-8 min-w-0">
        <div ref={bodyRef} className="md max-w-none">
        <Markdown remarkPlugins={[remarkGfm]}>{report.markdown}</Markdown>
        </div>

        {/* Reproducibility Signature Footer */}
        <div className="pt-8 border-t border-line/80 space-y-4 text-xs font-mono text-ink-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span>Report ID: {report.id}</span>
            <span>Verifier Version: {String((report.meta as Record<string, unknown> | undefined)?.verifier_version ?? "1.0")}</span>
            <span>Generated: {report.created_at}</span>
          </div>

        </div>
      </Card>
    </div>
  );
};
