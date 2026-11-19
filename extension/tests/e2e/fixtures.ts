import { chromium, test as base, type BrowserContext } from "@playwright/test";
import path from "node:path";

/** A Chromium with the built extension loaded. Run `npm run build` first. */
export const test = base.extend<{ context: BrowserContext }>({
  context: async ({}, use) => {
    const dist = path.resolve(import.meta.dirname, "../../.output/chrome-mv3");
    const context = await chromium.launchPersistentContext("", {
      channel: "chromium",
      args: [`--disable-extensions-except=${dist}`, `--load-extension=${dist}`, "--headless=new"],
    });
    await use(context);
    await context.close();
  },
});
export const expect = test.expect;
