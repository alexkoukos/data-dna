import { expect, test } from "./fixtures";

const IBAN = "GR1601101250000000012300695";
const received = async (request: import("@playwright/test").APIRequestContext) =>
  (await (await request.get("http://localhost:3100/api/received")).json()) as string[];

test.beforeEach(async ({ request }) => {
  await request.delete("http://localhost:3100/api/received");
});

test("an IBAN is masked before sending and restored in the answer", async ({
  context,
  request,
}) => {
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill(`Please pay ${IBAN} by Friday`);
  await page.locator("#prompt").press("Enter");

  await expect(page.locator(".msg.assistant")).toBeVisible();
  // The AI server only ever saw the placeholder.
  expect(await received(request)).toEqual(["Please pay [IBAN_1] by Friday"]);
  // The page shows the real value again, marked as restored locally.
  await expect(page.locator(".msg.assistant .sentry-restored")).toHaveText(IBAN);
});

test("clean text passes through untouched", async ({ context, request }) => {
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill("Summarise the meeting notes in three bullets");
  await page.locator("#send").click();
  await expect(page.locator(".msg.assistant")).toBeVisible();
  expect(await received(request)).toEqual(["Summarise the meeting notes in three bullets"]);
});

test("a value hidden with spaces asks first, and Send anyway goes through", async ({
  context,
  request,
}) => {
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill("tax id 1 2 3 4 5 6 7 8 3");
  await page.locator("#prompt").press("Enter");

  const card = page.getByRole("alertdialog");
  await expect(card).toBeVisible();
  await expect(card).toContainText("Let's check this before it leaves.");
  expect(await received(request)).toEqual([]);

  await card.getByRole("button", { name: "Send anyway" }).click();
  await expect(page.locator(".msg.assistant")).toBeVisible();
  expect(await received(request)).toEqual(["tax id 1 2 3 4 5 6 7 8 3"]);
});

test("Edit message cancels the send", async ({ context, request }) => {
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill("tax id 1 2 3 4 5 6 7 8 3");
  await page.locator("#prompt").press("Enter");
  await page.getByRole("alertdialog").getByRole("button", { name: "Edit message" }).click();
  await expect(page.getByRole("alertdialog")).toBeHidden();
  expect(await received(request)).toEqual([]);
  await expect(page.locator("#prompt")).toHaveValue("tax id 1 2 3 4 5 6 7 8 3");
});
