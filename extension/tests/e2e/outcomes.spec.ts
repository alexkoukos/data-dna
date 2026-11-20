import { readFileSync } from "node:fs";
import type { APIRequestContext } from "@playwright/test";
import { expect, test } from "./fixtures";

const BRAIN = process.env.BRAIN_URL ?? "http://localhost:8001";
const MOCK = "http://localhost:3100";
const IBAN = "GR1601101250000000012300695";

const sample = (lang: string, name: string) =>
  readFileSync(new URL(`../../../samples/${lang}/${name}.txt`, import.meta.url), "utf-8").trim();

/** The document outcomes need the full stack (documents registered, embedding model loaded). */
async function stackReady(request: APIRequestContext) {
  try {
    const r = await request.post(`${BRAIN}/v1/check`, {
      data: { text: sample("en", "5-block"), tool: "ChatGPT", url: "https://chatgpt.com/" },
      timeout: 15_000,
    });
    return r.ok() && (await r.json()).action === "block";
  } catch {
    return false;
  }
}

/** The extension waits only 400 ms for the brain, so a cold brain makes it fall back to offline.
 *  Send every sample once first so the real runs hit a warm one. */
let warmed = false;
async function warmUp(request: APIRequestContext) {
  if (warmed) return;
  warmed = true;
  test.afterEach(async ({ context, request }, info) => {
  if (info.status === info.expectedStatus) return;
  for (const page of context.pages()) {
    const text = await page.evaluate(() => document.body.innerText).catch(() => "?");
    const shadow = await page
      .evaluate(() =>
        [...document.querySelectorAll("*")]
          .map((e) => e.shadowRoot?.textContent?.trim() ?? "")
          .filter(Boolean)
          .join(" | "),
      )
      .catch(() => "?");
    console.log(`DIAG ${info.title} url=${page.url()}\nBODY: ${text.slice(0, 600)}\nSHADOW: ${shadow.slice(0, 600)}`);
  }
  console.log(`DIAG received: ${JSON.stringify(await received(request))}`);
});

for (const lang of ["en", "el"]) {
    for (const name of ["1-allow", "2-mask", "3-warn"]) {
      await request
        .post(`${BRAIN}/v1/check`, {
          data: { text: sample(lang, name), tool: "ChatGPT", url: "https://chatgpt.com/" },
          timeout: 30_000,
        })
        .catch(() => undefined);
    }
  }
}

const received = async (request: APIRequestContext) =>
  (await (await request.get(`${MOCK}/api/received`)).json()) as string[];

test.beforeEach(async ({ request }) => {
  test.skip(!(await stackReady(request)), "needs the full stack: make up (brain with documents)");
  await warmUp(request);
  await request.delete(`${MOCK}/api/received`);
});

for (const lang of ["en", "el"]) {
  test.describe(`${lang} samples, one for each outcome`, () => {
    test("1 allow: sent as written, nothing in the way", async ({ context, request }) => {
      const page = await context.newPage();
      await page.goto("/");
      const text = sample(lang, "1-allow");
      await page.locator("#prompt").fill(text);
      await page.locator("#prompt").press("Enter");
      await expect(page.locator(".msg.assistant")).toBeVisible();
      expect(await received(request)).toEqual([text]);
      await expect(page.getByRole("alertdialog")).toHaveCount(0);
    });

    test("2 mask: the AI sees placeholders, the page shows the real values", async ({
      context,
      request,
    }) => {
      const page = await context.newPage();
      await page.goto("/");
      await page.locator("#prompt").fill(sample(lang, "2-mask"));
      await page.locator("#prompt").press("Enter");
      await expect(page.locator(".msg.assistant")).toBeVisible();
      const [sent] = await received(request);
      expect(sent).toContain("[IBAN_1]");
      expect(sent).toContain("[AFM_1]");
      expect(sent).not.toContain("123456783");
      expect(sent).not.toContain("0110");
      await expect(page.locator(".msg.assistant .sentry-restored").first()).toBeVisible();
      await expect(page.locator(".msg.assistant")).toContainText("123456783");
      await expect(page.locator(".note")).toContainText("masked");
    });

    test("3 warn: a card asks first, Send anyway needs no reason but records one", async ({
      context,
      request,
    }) => {
      const page = await context.newPage();
      await page.goto("/");
      const text = sample(lang, "3-warn");
      await page.locator("#prompt").fill(text);
      await page.locator("#prompt").press("Enter");
      const card = page.getByRole("alertdialog");
      await expect(card).toContainText("Let's check this before it leaves.");
      await expect(card).toContainText("client name");
      expect(await received(request)).toEqual([]);
      await card.getByLabel(/Why do you need to send this/).fill("Follow-up the client asked for");
      await card.getByRole("button", { name: "Send anyway" }).click();
      await expect(page.locator(".msg.assistant")).toBeVisible();
      expect(await received(request)).toEqual([text]);
    });

    test("4 redirect: not sent, the card points to the company AI", async ({
      context,
      request,
    }) => {
      const page = await context.newPage();
      await page.goto("/");
      await page.locator("#prompt").fill(sample(lang, "4-redirect"));
      await page.locator("#prompt").press("Enter");
      const card = page.getByRole("alertdialog");
      await expect(card).toContainText("Company AI can answer this safely.");
      await expect(card).toContainText("Salary bands 2027");
      await expect(card.getByRole("button", { name: "Ask the company AI" })).toBeVisible();
      expect(await received(request)).toEqual([]);
    });

    test("5 block: not sent, says why and what to do instead", async ({ context, request }) => {
      const page = await context.newPage();
      await page.goto("/");
      await page.locator("#prompt").fill(sample(lang, "5-block"));
      await page.locator("#prompt").press("Enter");
      const card = page.getByRole("alertdialog");
      await expect(card).toContainText("This stays inside the company.");
      await expect(card).toContainText("Board memo");
      await expect(card).toContainText(/I stopped this send/);
      expect(await received(request)).toEqual([]);
      await card.getByRole("button", { name: "Edit message" }).click();
      await expect(page.locator("#prompt")).not.toHaveValue("");
    });
  });
}

test("the masked IBAN really is the one from the sample", async ({ request }) => {
  const r = await request.post(`${BRAIN}/v1/check`, {
    data: { text: sample("en", "2-mask"), tool: "ChatGPT", url: "https://chatgpt.com/" },
  });
  const body = await r.json();
  expect(body.placeholders["[IBAN_1]"].replaceAll(" ", "")).toBe(IBAN);
});
