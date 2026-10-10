import React, { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity,
  FileText,
  Hourglass,
  LayoutDashboard,
  ListChecks,
  Menu,
  Moon,
  Plus,
  ShieldAlert,
  ShieldCheck,
  Sun,
  Terminal,
  X,
} from "lucide-react";
import { API_MODE, useApi } from "../../api/client";
import type { Target } from "../../api/models";
import { currentTheme, setTheme, type Theme } from "../../lib/theme";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { NewRunDialog } from "../run/NewRunDialog";

// Only real, implemented capabilities; grouped by the order an engineer works in.
const NAV: { group: string; items: { to: string; label: string; icon: React.ReactNode; end?: boolean }[] }[] = [
  { group: "", items: [{ to: "/", label: "Overview", icon: <LayoutDashboard className="w-4 h-4" />, end: true }] },
  {
    group: "Investigate",
    items: [
      { to: "/findings", label: "Findings", icon: <ShieldAlert className="w-4 h-4" /> },
      { to: "/runs", label: "Runs", icon: <Terminal className="w-4 h-4" /> },
      { to: "/sleeper", label: "Sleeper testing", icon: <Hourglass className="w-4 h-4" /> },
    ],
  },
  {
    group: "Harden",
    items: [
      { to: "/permissions", label: "Permission analysis", icon: <ListChecks className="w-4 h-4" /> },
      { to: "/fixes", label: "Remediation", icon: <ShieldCheck className="w-4 h-4" /> },
    ],
  },
  { group: "Evidence", items: [{ to: "/report", label: "Reports", icon: <FileText className="w-4 h-4" /> }] },
];

function titleFor(path: string): string {
  if (path === "/privacy") return "Privacy";
  if (path === "/terms") return "Terms of use";
  for (const g of NAV) for (const i of g.items) if (i.end ? path === i.to : path.startsWith(i.to)) return i.label;
  return "AgentBreak";
}

const Nav: React.FC<{ onNavigate?: () => void }> = ({ onNavigate }) => (
  <nav aria-label="Main" className="flex flex-col gap-4 text-sm">
    {NAV.map((g) => (
      <div key={g.group || "home"}>
        {g.group && <p className="px-2.5 pb-1 text-[11px] font-medium text-ink-3">{g.group}</p>}
        <ul className="space-y-0.5">
          {g.items.map((i) => (
            <li key={i.to}>
              <NavLink
                to={i.to}
                end={i.end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-md px-2.5 py-1.5 transition-colors duration-150 ${
                    isActive ? "bg-action/10 text-action font-medium" : "text-ink-2 hover:text-ink hover:bg-surface-muted"
                  }`
                }
              >
                <span aria-hidden>{i.icon}</span>
                {i.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    ))}
  </nav>
);

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { pathname } = useLocation();
  const [theme, setThemeState] = useState<Theme>(() => currentTheme());
  const [drawer, setDrawer] = useState(false);
  const [newRun, setNewRun] = useState(false);
  const target = useApi<Target>("/targets/tgt_demo_scripted");

  useEffect(() => setDrawer(false), [pathname]);
  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawer(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer]);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  };

  const brand = (
    <div className="flex items-center gap-2 px-2.5">
      <span className="grid place-items-center w-7 h-7 rounded-md bg-action text-action-fg" aria-hidden>
        <Activity className="w-4 h-4" />
      </span>
      <span>
        <span className="block text-sm font-semibold text-ink leading-4">AgentBreak</span>
        <span className="block text-[11px] text-ink-3 leading-4">Agent security workbench</span>
      </span>
    </div>
  );

  return (
    <div className="min-h-screen bg-canvas text-ink lg:grid lg:grid-cols-[232px_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>

      <aside className="hidden lg:flex lg:flex-col gap-6 sticky top-0 h-screen border-r border-line bg-surface px-3 py-4">
        {brand}
        <Nav />
        <div className="mt-auto px-2.5 space-y-2 text-[11px] leading-4 text-ink-3">
          <p>Verdicts come only from PRE/POST state diffs and canaries, never from model text.</p>
          <p className="flex gap-3">
            <NavLink to="/privacy" className="hover:text-ink">
              Privacy
            </NavLink>
            <NavLink to="/terms" className="hover:text-ink">
              Terms
            </NavLink>
          </p>
        </div>
      </aside>

      {drawer && (
        <div className="lg:hidden fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-canvas/70" onClick={() => setDrawer(false)} aria-hidden />
          <div className="absolute inset-y-0 left-0 w-64 bg-surface border-r border-line px-3 py-4 flex flex-col gap-6">
            <div className="flex items-center justify-between">
              {brand}
              <button className="rounded-md p-1.5 text-ink-2 hover:bg-surface-muted" onClick={() => setDrawer(false)} aria-label="Close navigation">
                <X className="w-4 h-4" />
              </button>
            </div>
            <Nav onNavigate={() => setDrawer(false)} />
            <p className="mt-auto flex gap-3 px-2.5 text-[11px] text-ink-3">
              <NavLink to="/privacy">Privacy</NavLink>
              <NavLink to="/terms">Terms</NavLink>
            </p>
          </div>
        </div>
      )}

      <div className="min-w-0 flex flex-col">
        <header className="sticky top-0 z-30 h-14 border-b border-line bg-canvas flex items-center gap-3 px-4 sm:px-6">
          <button className="lg:hidden rounded-md p-1.5 text-ink-2 hover:bg-surface-muted" onClick={() => setDrawer(true)} aria-label="Open navigation">
            <Menu className="w-5 h-5" />
          </button>
          <p className="text-sm font-semibold text-ink truncate">{titleFor(pathname)}</p>
          {target.data && (
            <p className="hidden md:flex items-center gap-1.5 text-xs text-ink-2 min-w-0">
              <span className="text-ink-3">Target</span>
              <span className="font-mono text-ink truncate">{target.data.id}</span>
              <Badge variant="outline">{target.data.kind === "scripted" ? "simulated" : target.data.kind}</Badge>
              <span className="text-ink-3">policy</span>
              <span className="font-mono text-ink truncate">{target.data.active_policy_id ?? "none"}</span>
            </p>
          )}
          <div className="ml-auto flex items-center gap-2">
            {API_MODE === "mock" ? (
              <Badge variant="high">Mock fixtures, not live results</Badge>
            ) : (
              <Badge variant="allowed" className="hidden sm:inline-flex">
                Live API
              </Badge>
            )}
            <button
              onClick={toggleTheme}
              className="rounded-md p-1.5 text-ink-2 hover:text-ink hover:bg-surface-muted"
              aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              title={theme === "dark" ? "Light theme" : "Dark theme"}
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <Button size="sm" icon={<Plus className="w-3.5 h-3.5" />} onClick={() => setNewRun(true)}>
              New run
            </Button>
          </div>
        </header>
        <main id="main" className="flex-1 min-w-0 px-4 sm:px-6 py-6">
          {/* Route change: a short fade-in only (no exit delay); disabled under reduced motion via MotionConfig. */}
          <motion.div key={pathname.split("/")[1]} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.14 }}>
            {children}
          </motion.div>
        </main>
      </div>
      <NewRunDialog open={newRun} onClose={() => setNewRun(false)} />
    </div>
  );
};
