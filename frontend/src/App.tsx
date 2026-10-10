/**
 * Root Application Component
 * Sets up the browser routing context, renders the persistent animated Navbar,
 * and mounts the application route views.
 */
import React from "react";
import { BrowserRouter } from "react-router-dom";
import { Navbar } from "./components/layout/Navbar";
import { AppRoutes } from "./routes";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500/30 selection:text-emerald-200">
        <Navbar />
        <main className="flex-1">
          <AppRoutes />
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
