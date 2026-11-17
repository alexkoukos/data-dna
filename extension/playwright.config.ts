import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  use: { baseURL: "http://localhost:3100" },
  webServer: {
    command: "node ../mock-ai/server.mjs",
    url: "http://localhost:3100/healthz",
    reuseExistingServer: true,
  },
});
