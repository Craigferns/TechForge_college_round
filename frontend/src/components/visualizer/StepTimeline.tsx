import React, { useEffect } from "react";
import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw } from "lucide-react";
import type { SimulationStep } from "./types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

interface Props {
  steps: SimulationStep[];
  currentStepIdx: number;
  onStepChange: (idx: number) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onReset: () => void;
  isShielded: boolean;
}

export const StepTimeline: React.FC<Props> = ({
  steps,
  currentStepIdx,
  onStepChange,
  isPlaying,
  onTogglePlay,
  onReset,
  isShielded,
}) => {
  // Auto-play timer
  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      onStepChange(currentStepIdx >= steps.length - 1 ? 0 : currentStepIdx + 1);
    }, 2800);
    return () => clearInterval(timer);
  }, [isPlaying, currentStepIdx, steps.length, onStepChange]);

  const step = steps[currentStepIdx] || steps[0];

  return (
    <div className="rounded-lg border border-line bg-surface p-4 sm:p-5 space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Button
            variant={isPlaying ? "secondary" : "primary"}
            size="sm"
            onClick={onTogglePlay}
            icon={isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            aria-label={isPlaying ? "Pause simulation playback" : "Play simulation playback"}
          >
            {isPlaying ? "Pause" : "Play simulation"}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            disabled={currentStepIdx === 0}
            onClick={() => onStepChange(Math.max(0, currentStepIdx - 1))}
            icon={<ChevronLeft className="w-3.5 h-3.5" />}
            aria-label="Previous step"
          >
            Prev
          </Button>

          <Button
            variant="secondary"
            size="sm"
            disabled={currentStepIdx >= steps.length - 1}
            onClick={() => onStepChange(Math.min(steps.length - 1, currentStepIdx + 1))}
            icon={<ChevronRight className="w-3.5 h-3.5" />}
            aria-label="Next step"
          >
            Next
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
            aria-label="Reset to step 1"
          >
            Reset
          </Button>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-ink-3">Step {currentStepIdx + 1} of {steps.length}:</span>
          <span className="font-semibold text-ink">{step.title}</span>
          <Badge variant={isShielded ? "allowed" : "unauthorized"}>
            {isShielded ? "Protected mode" : "Unshielded mode"}
          </Badge>
        </div>
      </div>

      {/* Scrubber Nodes */}
      <div className="relative pt-2">
        <div className="absolute top-1/2 left-0 right-0 h-0.5 -translate-y-1/2 bg-line" aria-hidden />

        <div className="relative z-10 flex justify-between gap-1">
          {steps.map((s, idx) => {
            const active = idx === currentStepIdx;
            const completed = idx < currentStepIdx;

            return (
              <button
                key={s.idx}
                onClick={() => onStepChange(idx)}
                aria-label={`Step ${idx + 1}: ${s.title}`}
                aria-current={active ? "step" : undefined}
                className={`group flex flex-col items-center focus:outline-none focus-visible:ring-2 focus-visible:ring-action rounded-md p-1 transition-all ${
                  active ? "scale-105" : ""
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono font-bold transition-all ${
                    active
                      ? isShielded
                        ? "bg-ok text-action-fg ring-4 ring-ok/25 shadow-sm"
                        : "bg-vuln text-action-fg ring-4 ring-vuln/25 shadow-sm"
                      : completed
                        ? "bg-surface-raised border border-line-strong text-ink-2"
                        : "bg-surface-muted border border-line text-ink-3"
                  }`}
                >
                  {idx + 1}
                </div>
                <span
                  className={`mt-1.5 text-[10px] hidden sm:block max-w-[80px] text-center font-medium leading-tight truncate transition-colors ${
                    active ? "text-ink" : "text-ink-3"
                  }`}
                >
                  {s.title.split(":")[0]?.replace(/^\d+\.\s*/, "") || s.title}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
