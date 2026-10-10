/**
 * AgentBreak Application Route Tree
 * Maps all 7 core platform screens:
 * / -> Landing & 1-min demo runner
 * /dashboard -> KPI metrics & analytics
 * /runs/:runId -> Step trace replay & state diffs
 * /permissions -> D1 Permission Diff & attribution
 * /fixes -> D2 Fix Lab & Price Tags
 * /sleeper -> D3 Sleeper Mode multi-session timeline
 * /report -> Evidence Report generator & PDF export
 */
import React from "react";
import { Route, Routes } from "react-router-dom";
import { LandingPage } from "./pages/Landing";
import { DashboardPage } from "./pages/Dashboard";
import { RunDetailPage } from "./pages/RunDetail";
import { PermissionDiffPage } from "./pages/PermissionDiff";
import { FixLabPage } from "./pages/FixLab";
import { SleeperPage } from "./pages/Sleeper";
import { ReportPage } from "./pages/Report";

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/runs/:runId" element={<RunDetailPage />} />
      <Route path="/permissions" element={<PermissionDiffPage />} />
      <Route path="/fixes" element={<FixLabPage />} />
      <Route path="/sleeper" element={<SleeperPage />} />
      <Route path="/report" element={<ReportPage />} />
    </Routes>
  );
};
