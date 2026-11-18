/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 3000,
    host: true,
    // In dev, /api goes to the brain like nginx does in Docker.
    proxy: {
      "/api": {
        target: process.env.BRAIN_URL ?? "http://127.0.0.1:8001",
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: { reporter: ["text", "html"] },
  },
});
