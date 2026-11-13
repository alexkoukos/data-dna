import { defineConfig } from "@playwright/test";

// End-to-end tests run against the full stack: `make up`, then `npm run e2e`.
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: process.env.BASE_URL ?? "http://localhost:3000" },
  reporter: [["list"], ["html", { open: "never" }]],
});
