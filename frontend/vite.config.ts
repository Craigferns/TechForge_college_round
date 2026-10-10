/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Explicit IPv4 loopback: Node may otherwise bind only [::1], breaking http://127.0.0.1:5173.
    host: "127.0.0.1",
    port: 5173,
    strictPort: true, // fail loudly instead of silently moving to another port
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    env: { VITE_API_MODE: "mock" }, // tests never hit a live API
  },
});
