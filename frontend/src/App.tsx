import React from "react";
import { BrowserRouter } from "react-router-dom";
import { MotionConfig } from "framer-motion";
import { AppShell } from "./components/layout/AppShell";
import { AppRoutes } from "./routes";

export const App: React.FC = () => (
  // reducedMotion="user": every framer-motion animation honours prefers-reduced-motion.
  <MotionConfig reducedMotion="user">
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppShell>
        <AppRoutes />
      </AppShell>
    </BrowserRouter>
  </MotionConfig>
);

export default App;
