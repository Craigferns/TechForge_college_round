import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { DashboardPage } from "./pages/Dashboard";
import { FindingsPage } from "./pages/Findings";
import { RunDetailPage } from "./pages/RunDetail";
import { PermissionDiffPage } from "./pages/PermissionDiff";
import { FixLabPage } from "./pages/FixLab";
import { SleeperPage } from "./pages/Sleeper";
import { ReportPage } from "./pages/Report";
import { VisualizerPage } from "./pages/Visualizer";
import { PrivacyPage } from "./pages/Privacy";
import { TermsPage } from "./pages/Terms";

export const AppRoutes: React.FC = () => (
  <Routes>
    <Route path="/" element={<DashboardPage />} />
    <Route path="/dashboard" element={<Navigate to="/" replace />} />
    <Route path="/visualizer" element={<VisualizerPage />} />
    <Route path="/visualizer/:caseId" element={<VisualizerPage />} />
    <Route path="/findings" element={<FindingsPage />} />
    <Route path="/findings/:findingId" element={<FindingsPage />} />
    <Route path="/runs" element={<RunDetailPage />} />
    <Route path="/runs/:runId" element={<RunDetailPage />} />
    <Route path="/permissions" element={<PermissionDiffPage />} />
    <Route path="/permissions/:auditId" element={<PermissionDiffPage />} />
    <Route path="/fixes" element={<FixLabPage />} />
    <Route path="/fixes/:auditId" element={<FixLabPage />} />
    <Route path="/sleeper" element={<SleeperPage />} />
    <Route path="/sleeper/:sleeperId" element={<SleeperPage />} />
    <Route path="/report" element={<ReportPage />} />
    <Route path="/report/:reportId" element={<ReportPage />} />
    <Route path="/privacy" element={<PrivacyPage />} />
    <Route path="/terms" element={<TermsPage />} />
    <Route path="*" element={<p className="text-sm text-ink-2">No page at this address.</p>} />
  </Routes>
);
