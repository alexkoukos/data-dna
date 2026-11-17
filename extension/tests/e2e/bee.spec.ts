import AxeBuilder from "@axe-core/playwright";
import type { BrowserContext, Page } from "@playwright/test";
import { expect, test } from "./fixtures";

const IBAN = "GR1601101250000000012300695";
const AFM = "094014201";
const SAMPLE = `Η πληρωμή γίνεται στο ${IBAN}, ΑΦΜ ${AFM}.`;

const received = async (request: import("@playwright/test").APIRequestContext) =>
  (await (await request.get("http://localhost:3100/api/received")).json()) as string[];

test.beforeEach(async ({ request }) => {
  await request.delete("http://localhost:3100/api/received");
});

/** What the toolbar badge says for each open tab, read from the extension's service worker. */
async function badges(context: BrowserContext): Promise<string[]> {
  let [worker] = context.serviceWorkers();
  worker ??= await context.waitForEvent("serviceworker");
  return worker.evaluate(async () => {
    const tabs = await chrome.tabs.query({});
    const out: string[] = [];
    for (const t of tabs) {
      if (t.id !== undefined) out.push(await chrome.action.getBadgeText({ tabId: t.id }));
    }
    return out;
  });
}

const beeCount = (page: Page, selector = ".bee-wrap") =>
  page.evaluate(
    (sel) => document.querySelector("pyli-overlay")?.shadowRoot?.querySelectorAll(sel).length ?? 0,
    selector,
  );

/** Resolves with the first rectangle of `selector` seen in the overlay, or null after 3 s. */
const firstRect = (page: Page, selector: string) =>
  page.evaluate(
    (sel) =>
      new Promise<{ left: number; top: number; width: number; height: number } | null>(
        (resolve) => {
          const t = setInterval(() => {
            const el = document.querySelector("pyli-overlay")?.shadowRoot?.querySelector(sel);
            if (el) {
              clearInterval(t);
              const r = el.getBoundingClientRect();
              resolve({ left: r.left, top: r.top, width: r.width, height: r.height });
            }
          }, 5);
          setTimeout(() => {
            clearInterval(t);
            resolve(null);
          }, 3000);
        },
      ),
    selector,
  );

test("MASK: the bee flies, goes away within 1.5 s, and the badge counts the masked values", async ({
  context,
  request,
}) => {
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill(SAMPLE);
  // Watch the overlay from inside the page, so slow polling cannot miss the bee.
  const lifetime = page.evaluate(
    () =>
      new Promise<number | null>((resolve) => {
        let seen = 0;
        const t = setInterval(() => {
          const here = !!document
            .querySelector("pyli-overlay")
            ?.shadowRoot?.querySelector(".bee-wrap");
          if (here && !seen) seen = performance.now();
          if (!here && seen) {
            clearInterval(t);
            resolve(performance.now() - seen);
          }
        }, 10);
        setTimeout(() => {
          clearInterval(t);
          resolve(null);
        }, 5000);
      }),
  );
  await page.locator("#prompt").press("Enter");

  // The decision comes first: the AI server only ever sees placeholders, whatever the bee does.
  await expect(page.locator(".msg.assistant")).toBeVisible();
  expect((await received(request))[0]).toContain("[IBAN_1]");

  const seconds = await lifetime;
  expect(seconds, "a bee appeared and was removed").not.toBeNull();
  expect(seconds!).toBeLessThan(1500);
  expect(await beeCount(page)).toBe(0);
  await expect.poll(() => badges(context), { timeout: 3000 }).toContain("2");
  await expect(page.locator("pyli-overlay")).toBeAttached();
});

test("MASK with reduced motion: no bee is ever created, but the badge still counts", async ({
  context,
}) => {
  const page = await context.newPage();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.locator("#prompt").fill(SAMPLE);
  const sawBee = page.evaluate(
    () =>
      new Promise<boolean>((resolve) => {
        const t = setInterval(() => {
          if (document.querySelector("pyli-overlay")?.shadowRoot?.querySelector(".bee-wrap")) {
            clearInterval(t);
            resolve(true);
          }
        }, 5);
        setTimeout(() => {
          clearInterval(t);
          resolve(false);
        }, 2000);
      }),
  );
  await page.locator("#prompt").press("Enter");
  await expect(page.locator(".msg.assistant")).toBeVisible();
  expect(await sawBee).toBe(false);
  await expect.poll(() => badges(context), { timeout: 3000 }).toContain("2");
});

test("MASK: the bee starts on the exact text in a textarea, on a later line", async ({
  context,
}) => {
  const page = await context.newPage();
  await page.goto("/");
  const text = `first line\nsecond line\nthird line\nPlease pay ${IBAN} today`;
  await page.locator("#prompt").fill(text);
  const box = (await page.locator("#prompt").boundingBox())!;
  const glow = firstRect(page, ".bee-glow");
  await page.locator("#prompt").press("Enter");
  const r = (await glow)!;
  expect(r).not.toBeNull();
  // Inside the box, below the first three lines, and to the right of "Please pay ".
  expect(r.left).toBeGreaterThan(box.x + 40);
  expect(r.left + r.width).toBeLessThanOrEqual(box.x + box.width + 2);
  expect(r.top).toBeGreaterThan(box.y + 3 * 14);
  expect(r.top + r.height).toBeLessThanOrEqual(box.y + box.height + 2);
});

test("MASK: the bee starts on the exact text in a contenteditable composer", async ({
  context,
}) => {
  const page = await context.newPage();
  await page.route("http://localhost:3100/editable", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<!doctype html><title>editable</title><main id="messages"></main>
        <div id="prompt" contenteditable="true" role="textbox" aria-label="Message"
             style="width:480px;min-height:80px;border:1px solid #888;padding:8px;margin-top:200px"></div>
        <button id="send" type="button" onclick="document.getElementById('prompt').textContent=''">Send</button>`,
    }),
  );
  await page.goto("/editable");
  await page.locator("#prompt").pressSequentially(`short intro, then pay ${IBAN} today`);
  const box = (await page.locator("#prompt").boundingBox())!;
  const glow = firstRect(page, ".bee-glow");
  await page.locator("#prompt").press("Enter");
  const r = (await glow)!;
  expect(r).not.toBeNull();
  expect(r.left).toBeGreaterThan(box.x + 60);
  expect(r.top).toBeGreaterThanOrEqual(box.y);
  expect(r.top + r.height).toBeLessThanOrEqual(box.y + box.height + 2);
});

test("WARN: the bee lands on the card, and Esc closes the card and removes the bee", async ({
  context,
}) => {
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill("tax id 1 2 3 4 5 6 7 8 3");
  await page.locator("#prompt").press("Enter");
  const card = page.getByRole("alertdialog");
  await expect(card).toBeVisible();

  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const bee = document.querySelector("pyli-overlay")?.shadowRoot?.querySelector(".perch");
          return bee ? getComputedStyle(bee).visibility : "none";
        }),
      { timeout: 2000 },
    )
    .toBe("visible");

  await page.keyboard.press("Escape");
  await expect(card).toBeHidden();
  await expect.poll(() => beeCount(page), { timeout: 1500 }).toBe(0);
});

test("the bee never blocks the page: Send anyway still goes through while it moves", async ({
  context,
  request,
}) => {
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill("tax id 1 2 3 4 5 6 7 8 3");
  await page.locator("#prompt").press("Enter");
  const card = page.getByRole("alertdialog");
  await card.getByRole("button", { name: "Send anyway" }).click();
  await expect(page.locator(".msg.assistant")).toBeVisible();
  expect((await received(request)).length).toBe(1);
});

test("the warn card with the bee on it has no new accessibility violations", async ({
  context,
}) => {
  const page = await context.newPage();
  await page.goto("/");
  await page.locator("#prompt").fill("tax id 1 2 3 4 5 6 7 8 3");
  await page.locator("#prompt").press("Enter");
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await expect.poll(() => beeCount(page, ".perch"), { timeout: 2000 }).toBeGreaterThan(0);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(results.violations).toEqual([]);
});
