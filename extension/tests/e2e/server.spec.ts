import { expect, test } from "./fixtures";

const IBAN = "GR1601101250000000012300695";
const BRAIN = process.env.BRAIN_URL ?? "http://localhost:8001";

async function brainUp(request: import("@playwright/test").APIRequestContext) {
  try {
    return (await request.get(`${BRAIN}/healthz`, { timeout: 1500 })).ok();
  } catch {
    return false;
  }
}

test("with the company server up, the answer comes from the server", async ({
  context,
  request,
}) => {
  test.skip(!(await brainUp(request)), "needs the brain on :8001 (make up)");
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill(`Please pay ${IBAN} by Friday`);
  await page.locator("#prompt").press("Enter");
  await expect(page.locator(".note")).toContainText("1 item masked");
  await expect(page.locator(".note")).not.toContainText("not reached");
});

test("with the company server down, the browser still masks and says so", async ({
  context,
  request,
}) => {
  test.skip(await brainUp(request), "needs the brain to be stopped");
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill(`Please pay ${IBAN} by Friday`);
  await page.locator("#prompt").press("Enter");
  await expect(page.locator(".note")).toContainText("company server not reached");
});
