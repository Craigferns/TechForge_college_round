import React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;
}

const variants = {
  // Indigo is reserved for the single most important action in a context.
  primary: "bg-action text-action-fg hover:bg-action-hover shadow-sm",
  secondary: "bg-surface text-ink ring-1 ring-inset ring-line-strong hover:bg-surface-muted",
  danger: "bg-vuln/10 text-vuln ring-1 ring-inset ring-vuln/35 hover:bg-vuln/15",
  outline: "bg-transparent text-ink-2 ring-1 ring-inset ring-line-strong hover:text-ink hover:bg-surface-muted",
  ghost: "bg-transparent text-ink-2 hover:text-ink hover:bg-surface-muted",
};
const sizes = { sm: "h-8 px-2.5 text-xs gap-1.5", md: "h-9 px-3.5 text-sm gap-2", lg: "h-11 px-5 text-sm gap-2" };

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading = false, icon, children, disabled, type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      aria-busy={loading || undefined}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium select-none transition-colors duration-150 active:translate-y-px disabled:bg-disabled disabled:text-disabled-fg disabled:ring-line disabled:shadow-none disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  )
);
Button.displayName = "Button";
