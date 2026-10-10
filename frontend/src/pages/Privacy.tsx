import React from "react";

/** Describes what this build actually does with data. Update it whenever data handling changes. */
export const PrivacyPage: React.FC = () => (
  <article className="max-w-prose space-y-4 text-sm text-ink-2 leading-relaxed">
    <header>
      <h1 className="text-lg font-semibold text-ink">Privacy</h1>
      <p className="text-xs text-ink-3">Applies to AgentBreak v0.1.0 as distributed in this repository. Last reviewed 2026-10-11.</p>
    </header>
    <p>
      AgentBreak is self-hosted software. You run the API and this interface on your own machine. The project authors operate no
      server that receives your data, and the software sends no telemetry or analytics.
    </p>
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-ink">What is stored, and where</h2>
      <ul className="list-disc pl-5 space-y-1">
        <li>
          Runs, execution traces, environment snapshots, verdicts, findings, audits, fix evaluations and reports are written to a local
          SQLite file (<code className="text-term">AGENTBREAK_DB_PATH</code>, default <code className="text-term">./data/agentbreak.db</code>).
        </li>
        <li>
          The built-in test suite uses synthetic data only: <code className="text-term">.test</code> addresses and fake canary tokens.
          If you test a real agent, whatever it returns (tool calls and text) is stored in the same file.
        </li>
        <li>Your browser stores one value in local storage: the light or dark theme preference.</li>
      </ul>
    </section>
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-ink">Network and third parties</h2>
      <ul className="list-disc pl-5 space-y-1">
        <li>This interface only calls the local AgentBreak API. Fonts are bundled; no external assets are loaded.</li>
        <li>
          The API contacts only the target endpoint you configure, plus an optional attacker-model endpoint. Endpoints must be local or
          private unless you set <code className="text-term">AGENTBREAK_ALLOW_REMOTE_TARGETS=1</code>. If you point it at a hosted
          model provider, that provider's own privacy terms apply to what is sent.
        </li>
        <li>API keys are read from environment variables. AgentBreak stores the variable name, never the key.</li>
      </ul>
    </section>
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-ink">Retention and deletion</h2>
      <p>
        There is no automatic retention limit. Data stays until you delete the database file. The demo resets only the simulated demo
        target&apos;s active policy and finding statuses; it does not delete other records.
      </p>
    </section>
    <p className="text-xs text-ink-3">
      This page describes the software&apos;s behaviour. It is not a compliance certification. If you deploy AgentBreak for others, you are
      responsible for your own privacy notice.
    </p>
  </article>
);
