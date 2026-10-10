import React from "react";

export const TermsPage: React.FC = () => (
  <article className="max-w-prose space-y-4 text-sm text-ink-2 leading-relaxed">
    <header>
      <h1 className="text-lg font-semibold text-ink">Terms of use</h1>
      <p className="text-xs text-ink-3">AgentBreak v0.1.0, a hackathon prototype. Last reviewed 2026-10-11.</p>
    </header>
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-ink">License</h2>
      <p>
        No open-source license has been chosen for this repository yet. Until one is published, ask the repository owner before reusing or
        redistributing the code.
      </p>
    </section>
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-ink">Authorized testing only</h2>
      <p>
        Use AgentBreak only against agents, models and endpoints you own or are explicitly authorized to test. The bundled suite uses
        synthetic data; do not load real credentials, mailboxes or personal data into it.
      </p>
    </section>
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-ink">What results mean</h2>
      <p>
        Verdicts are computed from environment state before and after each run. Results against the simulated (scripted) target show
        that the measurement pipeline works; they are not evidence about the robustness of any real model. A passing run is not a
        security certification.
      </p>
    </section>
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-ink">No warranty</h2>
      <p>
        The software is provided as is, without warranty of any kind. The authors are not liable for damages arising from its use,
        including actions taken by agents you test with it.
      </p>
    </section>
  </article>
);
