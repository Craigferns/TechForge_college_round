# AgentBreak — UI/UX transformation report (2026-10-11)

**Final status (second pass, 30-rule audit): UI/UX REDESIGN PARTIALLY VERIFIED**. First pass: UI TRANSFORMATION PARTIALLY VERIFIED: the implementation is complete, and the main workflows were exercised live in a browser in both themes and at desktop and mobile widths. Some checks were not run (see §9).

## 1. Initial audit
- Stack: React 18, Vite 5, TypeScript strict, Tailwind 3 (`darkMode: "class"`, but no light theme existed), react-router 6, framer-motion, lucide, recharts, react-markdown. Testing was Vitest with jsdom in mock mode.
- The only theme was a dark slate one, hard-coded with 439 `slate-*`/`emerald-*`/`red-*` utility classes across 14 files. The `index.css` tokens were unused shadcn-style HSL variables.
- The shell was a top navbar that overflowed at about 800 px. A marketing hero on `/` pushed operational data below the fold.
- Truthfulness defects found during the audit (all fixed):
  - The run page hard-coded "EXPLOITED / HIGH SEVERITY", "1 file deleted, P-DELETE: TRUE", and a red classification colour on every run.
  - The verify banner was green even on a mismatch.
  - The sleeper trigger card was always red.
  - The backend attack graph always drew a "caused → Impact" edge, even when the attack was blocked (fixed in `domain/graph.py`, with a regression test).
- Usability defects: no Findings page despite a `/findings` API; no way to start a single run from the UI; trace and graph were not linked; the "state diff" was two full JSON dumps; Markdown reports were unstyled and their tables rendered as raw pipes (no GFM); API errors were drawn in the vulnerability red.

## 2. Design system
- **Tokens** (`src/index.css`, RGB channels so opacity modifiers work):
  - The supplied palette exactly: background, surface, text, secondary text, primary action, terminal, border and warning, for light and dark.
  - Plus `surface-raised/muted`, `text-tertiary`, `border-strong`, `action-hover/foreground` and `focus-ring`.
  - Security states: `vuln` (confirmed vulnerability), `ok` (blocked attack or benign pass), `running`, `inconclusive`, `infra` (infrastructure failure, deliberately magenta so it never reads as a vulnerability) and `info`.
  - `tailwind.config.js` maps every colour to a token. No component uses a raw hex value.
- **Contrast, measured with the WCAG formula:**
  - All dark-theme text tokens are ≥ 4.24:1 against surface and muted (ink-tertiary 4.24; every other text token ≥ 4.9).
  - In light mode, the supplied `#059669` (3.44:1) and `#EA580C` (3.25:1) fail AA for small text. They stay as the role colours for fills, rings and large numerals. Small text uses same-hue ink variants: `#047857` at 5.0:1 and `#C2410C` at 4.7:1. Light vuln, infra and info were darkened to pass AA as well.
  - Primary buttons: 6.29:1 (light) and 5.98:1 (dark).
- **Type:** IBM Plex Sans and Plex Mono, bundled with `@fontsource` so offline demos keep the type. Mono is used only for identifiers, code and numbers.
- **Theme:** a class-based light/dark switch in the top bar, persisted to `localStorage`, defaulting to the OS preference. An inline script in `index.html` applies it before first paint, so there's no flash.

## 3. Components and pages
- **Primitives:**
  - Button: one indigo primary per context.
  - Badge: gained the running, inconclusive, infra and info states.
  - Card: flat border; the glass and glow effects were removed.
  - Modal: `role=dialog`, labelled, focus moved in, Tab trapped, focus restored, Escape closes.
  - PageState: skeleton loading, error in infra colour, actionable empty state.
  - New: CopyButton and SeverityBadge.
- **AppShell:**
  - A grouped sidebar with real routes only (Overview / Investigate / Harden / Evidence) and a mobile drawer.
  - The top bar shows the page title, the real target and active policy, Live API or Mock badge, theme switch and **New run**.
  - A skip link. `/dashboard` redirects to `/`.
- **Overview:** posture tiles, each linking to its records; findings needing attention; severity bars (recharts removed); coverage by scenario; recent runs with clickable rows and truthful outcome labels; Run full demo with real backend progress.
- **Findings (new):** search, severity and status filters, sortable columns with `aria-sort`, and a split detail panel at `/findings/:id`. The panel shows measured evidence from the latest run and links to the trace, permissions and remediation.
- **New run (new):** a dialog for target, policy and attack case → `POST /runs`, then polls the real status with an indeterminate indicator and navigates to the run.
- **Run investigation:**
  - A verdict-derived header and a verify banner that shows match or mismatch truthfully.
  - An **attack path synchronised with the trace**: clicking a step node selects the trace step and the reverse. The final node is labelled as derived from the stored verdict.
  - Trace filters (all / flagged / tool calls / tool results / messages) and arrow-key navigation.
  - Step detail with copyable arguments and content; injected text is marked untrusted.
  - A real path-level **state diff** (changed / added / removed), with raw snapshots behind a disclosure; evidence and reproduce tabs.
- **Permission analysis:**
  - A dense table: tool, status, benign use, exploits enabled (counterfactual), benign broken if removed, and evidence-derived scope.
  - A before/after diff of the audited policy against the active policy, from `/policies/{a}/diff/{b}`.
- **Remediation:**
  - Suggested, measured and applied are separate states.
  - Measured results come first, with the price tag, Pareto status, Applied (active), expandable evidence and retest.
  - Apply uses a confirmation dialog that shows the measured cost.
- **Sleeper testing:** outcome-driven banner and session cards (planted / dormant / fired or blocked), session numbers from the data, and links to session traces.
- **Report:** token-styled Markdown with GFM tables (`remark-gfm`; raw HTML is still not rendered).

## 4. Motion
- framer-motion (already installed) is used only for dialog enter and exit (150–200 ms) and the attack-path connectors, which draw in once (250 ms, staggered by 120 ms).
- Hover and active feedback uses CSS transitions of about 150 ms. No looping animation except loading spinners and skeleton pulses.
- `MotionConfig reducedMotion="user"`, plus a global `prefers-reduced-motion` CSS rule that zeroes transitions and animations. Skeletons use `motion-safe:animate-pulse`.

## 5. Accessibility
- Semantic headings and tables, `aria-current` / `aria-pressed` / `aria-selected` / `aria-sort`, and `aria-live` for job status and copy feedback.
- A global `:focus-visible` ring, accessible names on icon buttons, and labelled form controls.
- Status is never carried by colour alone: every badge has text, and the diff uses −/+/~ symbols.

## 6. Files changed
- **Frontend, new:** `components/layout/AppShell.tsx`, `components/demo/DemoRunner.tsx`, `components/run/{NewRunDialog,AttackPath,StateDiff}.tsx`, `components/ui/{CopyButton,SeverityBadge}.tsx`, `lib/{theme,status}.ts`, `pages/Findings.tsx`.
- **Frontend, rewritten:** `index.css`, `tailwind.config.js`, `index.html`, `main.tsx`, `App.tsx`, `routes.tsx`, `components/ui/{Badge,Button,Card,Modal,PageState}.tsx`, `pages/{Dashboard,RunDetail,PermissionDiff,FixLab}.tsx`.
- **Frontend, edited:** `pages/{Sleeper,Report}.tsx`, `mocks/index.ts`, tests.
- **Frontend, removed:** `pages/Landing.tsx`, `components/layout/Navbar.tsx`.
- **Dependencies:** added `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono` and `remark-gfm`; removed `recharts`. The JS bundle went from 996 kB to 687 kB.
- **Backend:** `domain/graph.py` (no impact node unless the verdict confirms one; denied calls labelled) and its test.

## 7. Tests and build
| Check | Result |
|---|---|
| `npm run typecheck` / `lint` | clean / clean (0 warnings) |
| `npm test` | 10 passed: shell nav, theme toggle + persistence, per-page smoke, findings filter/search, attack-path → trace sync |
| `npm run build` | passes |
| Backend `pytest` / ruff / mypy / `check_mocks.py` | 122 passed / clean / clean / 29/29 |

## 8. Browser verification (live API, built-in browser)
- Overview, Findings (row → detail and deep link), Runs (exploited and blocked runs, state diff tab), Permissions, Remediation, Sleeper and Report were all inspected at 1440 px in dark and light.
- Mobile at 375 px: no horizontal overflow (`scrollWidth == innerWidth`); the drawer opens, navigates and closes.
- New run → AS-04 under the hardened policy → the run page shows **Not exploited (blocked)**, with `delete_file` denied by policy and no impact node.
- Dialog focus moves inside, and it is labelled.
- A fresh tab across all routes logged no console errors, and every API call returned 200.

## 9. Not verified, and limitations
- **Reduced motion:** implemented, but not exercised with OS emulation.
- **Keyboard and screen reader:** no screen-reader pass; the trace arrow-key navigation and the dialog focus trap were not exercised with a real keyboard.
- **Tablet width (768 px):** not inspected.
- **Hard-coded target:** the target context is the demo target, because the API has no "current target" concept.
- **Table scale:** tables are client-filtered over at most 200 rows. Larger datasets need server-side filtering and pagination.
- **Graph shape:** the attack graph is linear because the backend records one vector → injected result → call → impact chain. Branching paths are not modelled.

## 10. Next improvements
Server-side filtering and pagination for runs and findings; a runs list page; target management UI; a reduced-motion and screen-reader audit; Playwright end-to-end tests for the demo flow.

## Second pass: 30-rule anti-pattern audit (2026-10-11)
See `UI_UX_ANTI_PATTERN_AUDIT.md` for the rule-by-rule table and evidence.
- **Removed:** glass blur (header, modal scrim), em dashes in UI and report copy.
- **Added:** `--scrim` and `--disabled-*` tokens.
- **Before/after remediation:** `FixEvalDetails.before_runs/after_runs` (additive) plus `components/fix/BeforeAfter.tsx`.
- **Report exports:** JSON and HTML.
- **Pages:** `/privacy` and `/terms`, written from the code's actual behaviour.
- **Finding detail:** observed facts separated from interpretation.
- **Motion:** route fade.
- **Fixes:**
  - The `/reports` mock returned a non-page.
  - `useByIdOrLatest` is hardened against malformed lists.
  - Mobile overflow on `/report` (unwrapped actions, long hashes in Markdown).
- **Files:**
  - New: `components/fix/BeforeAfter.tsx`, `pages/{Privacy,Terms}.tsx`.
  - Edited: `index.css`, `tailwind.config.js`, `index.html`, `AppShell.tsx`, `Modal.tsx`, `Button.tsx`, `DemoRunner.tsx`, `StateDiff.tsx`, `Dashboard.tsx`, `Findings.tsx`, `PermissionDiff.tsx`, `FixLab.tsx`, `Report.tsx`, `routes.tsx`, `api/client.ts`, `mocks/index.ts` + regenerated fixtures, `pages.test.tsx`.
  - Backend: `engine/measure.py`, `engine/fixes.py`, `schemas/fix.py`, `domain/report.py`, `openapi.json`, `api/types.ts`.
- **Results:** frontend 13 tests, lint, types and build pass. Backend 122 passed; ruff, mypy, mocks 29/29.
- **Browser checks:** 375 px overflow check on all routes; live retest showing before/after.
- **Still not verified:** reduced-motion emulation, screen reader, tablet width.
