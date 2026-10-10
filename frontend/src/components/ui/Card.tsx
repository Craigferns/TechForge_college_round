import React from "react";
import { cn } from "../../lib/utils";

export const Card: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, children, ...props }) => (
  <section className={cn("rounded-lg border border-line bg-surface p-4 sm:p-5", className)} {...props}>
    {children}
  </section>
);

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, children, ...props }) => (
  <div className={cn("flex flex-col gap-1 pb-3", className)} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({ className, children, ...props }) => (
  <h2 className={cn("text-sm font-semibold text-ink", className)} {...props}>
    {children}
  </h2>
);

export const CardDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({ className, children, ...props }) => (
  <p className={cn("text-xs text-ink-2 leading-relaxed", className)} {...props}>
    {children}
  </p>
);
