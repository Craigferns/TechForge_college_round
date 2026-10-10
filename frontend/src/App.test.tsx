import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("app shell", () => {
  it("renders the grouped sidebar navigation", () => {
    render(<App />);
    for (const label of ["Overview", "Findings", "Runs", "Sleeper testing", "Permission analysis", "Remediation", "Reports"]) {
      expect(screen.getAllByRole("link", { name: label }).length).toBeGreaterThan(0);
    }
    expect(screen.getByText("Mock fixtures, not live results")).toBeInTheDocument();
  });

  it("theme switch toggles the root class and persists the choice", () => {
    document.documentElement.classList.remove("dark");
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem("agentbreak-theme")).toBe("dark");
    fireEvent.click(screen.getByRole("button", { name: "Switch to light theme" }));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(localStorage.getItem("agentbreak-theme")).toBe("light");
  });
});
