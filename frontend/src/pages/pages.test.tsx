import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../routes";

// Mock mode (vite.config.ts test.env). Each page must reach its loaded state from fixtures,
// via both the "latest" route and the explicit-id route the demo links to.
function at(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>
  );
}

describe("page smoke tests (mock fixtures)", () => {
  it("dashboard shows posture tiles", async () => {
    at("/dashboard");
    expect(await screen.findByText("Attacks succeeding now")).toBeInTheDocument();
    expect(await screen.findByText("Attack coverage by scenario")).toBeInTheDocument();
  });

  it("permissions loads latest audit and by id", async () => {
    at("/permissions");
    expect(await screen.findByText("Minimal policy keeps")).toBeInTheDocument();
    at("/permissions/aud_1f3a9c02");
    expect((await screen.findAllByText("Minimal policy keeps")).length).toBeGreaterThan(0);
  });

  it("fix lab lists suggestions and measured fixes for an audit", async () => {
    at("/fixes/aud_1f3a9c02");
    expect(await screen.findByText("Measured fixes")).toBeInTheDocument();
    expect(await screen.findByText("Suggestions from audit evidence")).toBeInTheDocument();
  });

  it("sleeper shows the recorded outcome, not a fixed banner", async () => {
    at("/sleeper/slp_demo_as05");
    expect(await screen.findByText("Sleeper exploit confirmed:")).toBeInTheDocument();
  });

  it("run replay opens the latest attack run", async () => {
    at("/runs");
    expect((await screen.findAllByText(/_as-04/)).length).toBeGreaterThan(0);
  });

  it("report renders markdown", async () => {
    at("/report/rep_demo_7fa2");
    expect(await screen.findByRole("group", { name: "Export report" })).toBeInTheDocument();
  });

  it("findings filter changes the visible rows and a row opens the detail", async () => {
    at("/findings");
    const table = await screen.findByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(8); // header + 7 recorded findings
    fireEvent.change(screen.getByLabelText("Severity"), { target: { value: "high" } });
    expect(within(table).getAllByRole("row")).toHaveLength(3); // AS-04, AS-05
    fireEvent.change(screen.getByLabelText("Search findings"), { target: { value: "AS-04" } });
    expect(within(table).getAllByRole("row")).toHaveLength(2);
  });

  it("selecting an attack-path node selects the matching trace step", async () => {
    at("/runs");
    const node = await screen.findByRole("button", { name: /delete_file call/ });
    fireEvent.click(node);
    expect(node).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: /Step 7: tool call/ })).toBeInTheDocument();
  });

  it("privacy and terms pages describe real data handling", async () => {
    at("/privacy");
    expect(await screen.findByRole("heading", { name: "Privacy" })).toBeInTheDocument();
    expect(screen.getByText(/sends no telemetry/)).toBeInTheDocument();
    at("/terms");
    expect(await screen.findByRole("heading", { name: "Terms of use" })).toBeInTheDocument();
  });

  it("expanding a measured fix shows the per-case before/after comparison", async () => {
    at("/fixes");
    const toggles = await screen.findAllByRole("button", { name: /^Details for / });
    fireEvent.click(toggles[0]);
    expect(await screen.findByText("Before and after, per case")).toBeInTheDocument();
    expect(await screen.findByText("Outcome of each case under the base policy and the fixed policy")).toBeInTheDocument();
  });

  it("report exports produce valid JSON and a standalone HTML document", async () => {
    const blobs: Blob[] = [];
    URL.createObjectURL = vi.fn((b: Blob) => {
      blobs.push(b);
      return "blob:test";
    });
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    at("/report");
    await screen.findByRole("group", { name: "Export report" });
    await screen.findByRole("heading", { name: /Permission attribution/ });
    fireEvent.click(screen.getByRole("button", { name: "JSON" }));
    fireEvent.click(screen.getByRole("button", { name: "HTML" }));
    const read = (b: Blob) => new Promise<string>((res) => { const r = new FileReader(); r.onload = () => res(String(r.result)); r.readAsText(b); });
    const json = JSON.parse(await read(blobs[0]));
    expect(json.markdown).toContain("AgentBreak evidence report");
    const html = await read(blobs[1]);
    expect(html.startsWith("<!doctype html>")).toBe(true);
    expect(html).toContain("<table>");
    expect(html).not.toContain("<script");
    expect(click).toHaveBeenCalledTimes(2);
  });

  it("threat visualizer renders pipeline, toggles defense shield, and switches scenarios", async () => {
    at("/visualizer");
    expect(await screen.findByRole("heading", { name: /Agent Threat & Defense Visualizer/ })).toBeInTheDocument();
    expect(screen.getByText("1. Threat Carrier")).toBeInTheDocument();
    expect(screen.getByText("2. Agent Core (LLM)")).toBeInTheDocument();
    expect(screen.getByText("3. Policy Shield")).toBeInTheDocument();
    expect(screen.getByText("4. Host Sandbox")).toBeInTheDocument();

    // Toggle shield
    const shieldBtn = screen.getByRole("button", { name: /Shield Active: Hardened Policy/ });
    fireEvent.click(shieldBtn);
    expect(screen.getByText("UNPROTECTED")).toBeInTheDocument();
    expect(screen.getByText("UNPROTECTED: Raw Agent Exposed to Malicious Tool Calls")).toBeInTheDocument();

    // Toggle back
    fireEvent.click(screen.getByRole("button", { name: /Shield Off: Raw Agent/ }));
    expect(screen.getByText("SHIELD ARMED")).toBeInTheDocument();

    // Switch scenario to AS-01
    const as01Btn = screen.getByRole("button", { name: /AS-01/ });
    fireEvent.click(as01Btn);
    expect(screen.getByText(/Indirect Prompt Injection -> Credential Exfiltration/)).toBeInTheDocument();

    // Step timeline forward
    const nextBtn = screen.getByRole("button", { name: "Next step" });
    fireEvent.click(nextBtn);
    expect(screen.getAllByText("2. Poisoned Email Ingested").length).toBeGreaterThan(0);
  });
});

