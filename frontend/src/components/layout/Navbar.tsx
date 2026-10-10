import React from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Shield, Sparkles, Terminal, Activity, FileText, CheckCircle2, Sliders } from "lucide-react";
import { Badge } from "../ui/Badge";

export const Navbar: React.FC = () => {
  const location = useLocation();

  const navLinks = [
    { path: "/dashboard", label: "Dashboard", icon: <Activity className="w-4 h-4" /> },
    { path: "/runs/run_demo_as04", label: "Run Replay", icon: <Terminal className="w-4 h-4" /> },
    { path: "/permissions", label: "Permissions", icon: <Shield className="w-4 h-4" /> },
    { path: "/fixes", label: "Fix Lab", icon: <Sliders className="w-4 h-4" /> },
    { path: "/sleeper", label: "Sleeper", icon: <Sparkles className="w-4 h-4" /> },
    { path: "/report", label: "Report", icon: <FileText className="w-4 h-4" /> },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md px-6 py-3.5 flex items-center justify-between">
      {/* Brand */}
      <div className="flex items-center space-x-6">
        <Link to="/" className="flex items-center space-x-2.5 group cursor-pointer">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-lg font-bold tracking-tight text-white group-hover:text-emerald-400 transition">
                AgentBreak
              </span>
              <Badge variant="outline" className="text-[10px] py-0 px-1.5 font-mono text-emerald-400 border-emerald-500/30">
                v0.1.0
              </Badge>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">Autonomous Agent Security Platform</p>
          </div>
        </Link>

        {/* Target Indicator */}
        <div className="hidden lg:flex items-center gap-2 pl-4 border-l border-slate-800 text-xs text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Target:</span>
          <span className="font-mono text-slate-200 bg-slate-900 px-2 py-0.5 rounded-md border border-slate-800">
            demo-scripted (simulated)
          </span>
        </div>
      </div>

      {/* Navigation Links with animated layoutId */}
      <nav className="hidden md:flex items-center space-x-1">
        {navLinks.map((item) => {
          const isActive = location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path));
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`relative px-3.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-2 transition ${
                isActive ? "text-white" : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="navIndicator"
                  className="absolute inset-0 rounded-xl bg-slate-800/80 border border-slate-700/60"
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
              <span className="relative z-10">{item.icon}</span>
              <span className="relative z-10">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Status & Mode Badge */}
      <div className="flex items-center space-x-3">
        <Badge variant="allowed" icon={<CheckCircle2 className="w-3 h-3 text-emerald-400" />}>
          Sandbox Mock Mode
        </Badge>
      </div>
    </header>
  );
};
