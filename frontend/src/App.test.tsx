import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App smoke tests", () => {
  it("renders the navigation header with AgentBreak title", () => {
    render(<App />);
    const titles = screen.getAllByText("AgentBreak");
    expect(titles.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Permissions")).toBeInTheDocument();
    expect(screen.getByText("Fix Lab")).toBeInTheDocument();
    expect(screen.getByText("Sleeper")).toBeInTheDocument();
    expect(screen.getByText("Report")).toBeInTheDocument();
  });
});
