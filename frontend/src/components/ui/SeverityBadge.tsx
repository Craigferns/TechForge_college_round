import React from "react";
import { Badge } from "./Badge";

export const SeverityBadge: React.FC<{ severity: string }> = ({ severity }) => (
  <Badge variant={severity === "critical" ? "critical" : severity === "high" ? "high" : severity === "medium" ? "medium" : "low"}>
    {severity[0].toUpperCase() + severity.slice(1)}
  </Badge>
);
