import { defineConfig } from "@playwright/test";

// End-to-end tests run against the full stack: `make up`, then `npm run e2e`.
export default defineConfig({
  testDir: "./e2e",
  // reducedMotion: the product animates everywhere, and axe samples colors mid-fade otherwise.
  use: { baseURL: process.env.BASE_URL ?? "http://localhost:3000", reducedMotion: "reduce" },
  reporter: [["list"], ["html", { open: "never" }]],
});
