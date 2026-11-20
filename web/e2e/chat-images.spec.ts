import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Pictures in Company Chat against the full stack (`make up`). The fixtures are synthetic, see
// e2e/fixtures/README.md. The picture itself goes to the model, after the gate has read it.
const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = (name: string) => path.join(here, "fixtures", name);
const composerInput = (page: Page) => page.locator('input[type="file"]').last();

test.describe.configure({ timeout: 120_000 }); // reading pictures is CPU work on a busy machine

test.beforeEach(async ({ page }) => {
  await page.goto("/chat");
  const types = await page.request.get("/api/v1/files/limits").then((r) => r.json());
  test.skip(!types.types.includes(".png"), "the server has no OCR, so it does not take images");
});

test("a chart is read, sent as a picture and answered", async ({ page }) => {
  await composerInput(page).setInputFiles(fixture("chart.png"));
  await expect(page.getByText("· Ready")).toBeVisible({ timeout: 60_000 });
  await page.getByRole("textbox", { name: "Your question" }).fill("Which quarter was best?");
  const request = page.waitForRequest((r) => r.url().includes("/gateway/v1/chat/completions"));
  await page.getByRole("button", { name: "Send" }).click();
  const body = (await request).postDataJSON() as {
    messages: { content: string | { type: string; image_url?: { url: string } }[] }[];
  };
  const parts = body.messages.at(-1)!.content;
  expect(Array.isArray(parts)).toBe(true);
  // Redrawn in the browser as JPEG: no metadata, nothing hidden under transparency.
  expect((parts as { image_url?: { url: string } }[])[1]?.image_url?.url).toMatch(
    /^data:image\/jpeg;base64,/,
  );
  await expect(page.getByText(/^Allowed\s*· chart\.png$/)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("img", { name: "chart.png" })).toBeVisible();
});

test("a picture with text a person cannot see is blocked, and says why", async ({ page }) => {
  await composerInput(page).setInputFiles(fixture("chart-hidden-text.png"));
  await expect(page.getByText("· Ready")).toBeVisible({ timeout: 60_000 });
  await page.getByRole("textbox", { name: "Your question" }).fill("Summarise this chart");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/^Blocked\s*· chart-hidden-text\.png$/)).toBeVisible({
    timeout: 60_000,
  });
  await page.getByRole("button", { name: /sentry_check/ }).click();
  await expect(page.getByText(/text hidden in an image/)).toBeVisible();
});

test("/chat with a picture attached is accessible on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await composerInput(page).setInputFiles(fixture("chart.png"));
  await expect(page.getByText("· Ready")).toBeVisible({ timeout: 60_000 });
  await page.waitForLoadState("networkidle");
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? "")),
  ).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(
    false,
  );
});
