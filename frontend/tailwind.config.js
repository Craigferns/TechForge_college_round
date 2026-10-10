/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        border: "hsl(var(--border))",
        // Semantic security tokens
        injected: {
          DEFAULT: "#F59E0B",
          bg: "#FEF3C7",
          dark: "#D97706",
        },
        unauthorized: {
          DEFAULT: "#EF4444",
          bg: "#FEE2E2",
          dark: "#DC2626",
        },
        allowed: {
          DEFAULT: "#10B981",
          bg: "#D1FAE5",
          dark: "#059669",
        },
        denied: {
          DEFAULT: "#64748B",
          bg: "#F1F5F9",
          dark: "#475569",
        },
      },
    },
  },
  plugins: [],
}
