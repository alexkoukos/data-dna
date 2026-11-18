import AxeBuilder from "@axe-core/playwright";
import type { BrowserContext } from "@playwright/test";
import { expect, test } from "./fixtures";

async function extensionId(context: BrowserContext) {
  let [worker] = context.serviceWorkers();
  worker ??= await context.waitForEvent("serviceworker");
  return new URL(worker.url()).host;
}

for (const name of ["popup", "options", "sidepanel"]) {
  test(`${name} page has no accessibility violations`, async ({ context }) => {
    const id = await extensionId(context);
    const page = await context.newPage();
    await page.goto(`chrome-extension://${id}/${name}.html`);
    await expect(page.locator("h1")).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(results.violations).toEqual([]);
  });
}

test("the side panel says so when the company AI cannot be reached", async ({ context }) => {
  const id = await extensionId(context);
  const page = await context.newPage();
  await page.goto(`chrome-extension://${id}/sidepanel.html`);
  await page.getByLabel("Your question").fill("Summarise our travel policy");
  await page.getByRole("button", { name: "Ask company AI" }).click();
  // The answer bubble and the note under it both say so; either one is enough.
  await expect(
    page.getByText(/could not be reached|Answered locally|Stand-in answer/).first(),
  ).toBeVisible();
});
