import React, { useState } from "react";
import { Check, Copy } from "lucide-react";

export const CopyButton: React.FC<{ text: string; label: string }> = ({ text, label }) => {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          // Clipboard blocked: the text stays selectable on screen.
        }
      }}
      className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-ink-2 hover:text-ink hover:bg-surface-muted"
      aria-label={copied ? `${label} copied` : label}
    >
      {copied ? <Check className="w-3.5 h-3.5 text-term" aria-hidden /> : <Copy className="w-3.5 h-3.5" aria-hidden />}
      <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
    </button>
  );
};
