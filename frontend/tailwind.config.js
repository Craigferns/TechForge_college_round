/** @type {import('tailwindcss').Config} */
const t = (v) => `rgb(var(${v}) / <alpha-value>)`;

// All colours resolve to the theme tokens in src/index.css (light + .dark).
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        canvas: t("--background"),
        surface: { DEFAULT: t("--surface"), raised: t("--surface-raised"), muted: t("--surface-muted") },
        ink: { DEFAULT: t("--text-primary"), 2: t("--text-secondary"), 3: t("--text-tertiary") },
        action: { DEFAULT: t("--action-primary"), hover: t("--action-primary-hover"), fg: t("--action-primary-foreground") },
        term: { DEFAULT: t("--terminal-ink"), brand: t("--terminal-text") }, // text-term is the AA ink variant
        line: { DEFAULT: t("--border"), strong: t("--border-strong") },
        warn: { DEFAULT: t("--warning"), ink: t("--warning-ink") },
        vuln: t("--state-vuln"),
        ok: t("--state-ok"),
        running: t("--state-running"),
        inconclusive: t("--state-inconclusive"),
        infra: t("--state-infra"),
        info: t("--state-info"),
        scrim: t("--scrim"),
        disabled: { DEFAULT: t("--disabled-surface"), fg: t("--disabled-text") },
      },
      boxShadow: { raised: "var(--shadow-raised)" },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
