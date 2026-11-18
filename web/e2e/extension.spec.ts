// X27: the browser extension, run against a saved copy of the ChatGPT composer
// (extension/test/fixture.html) and a stand-in brain, so it needs neither the live site nor `make up`.
import { chromium, expect, test, type BrowserContext, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createServer, type Server } from "node:http";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const EXT = resolve(fileURLToPath(new URL(".", import.meta.url)), "../../extension");
const FIXTURE = readFileSync(resolve(EXT, "test/fixture.html"), "utf8");
const PORT = 8011;
const IBAN = "GR1601101250000000012300695";

type Call = { path: string; auth: string | undefined; body: Record<string, unknown> };
let server: Server | null = null;
let calls: Call[] = [];
let shadow = false;

function verdict(text: string) {
  const base = {
    reasons: ["Test reason"],
    entity_types: [] as string[],
    masked_text: null,
    shadow: false,
    alternative: "Company AI",
    alternative_url: "http://localhost:3000/chat",
    user_id: "maria",
  };
  if (shadow) return { ...base, decision: "allow", shadow: true, would_have: "block" };
  if (text.includes(IBAN)) {
    return {
      ...base,
      decision: "mask",
      entity_types: ["IBAN"],
      masked_text: text.replace(IBAN, "[IBAN_1]"),
    };
  }
  if (text.includes("CARD")) return { ...base, decision: "warn" };
  if (text.includes("SECRET"))
    return { ...base, decision: "block", reasons: ["Confidential document"] };
  return { ...base, decision: "allow", reasons: [] };
}

function startBrain(): Promise<void> {
  return new Promise((ok) => {
    server = createServer((req, res) => {
      let raw = "";
      req.on("data", (c) => (raw += c));
      req.on("end", () => {
        const body = raw ? JSON.parse(raw) : {};
        calls.push({ path: req.url ?? "", auth: req.headers.authorization, body });
        res.setHeader("content-type", "application/json");
        if (req.url === "/v1/extension/inspect")
          res.end(JSON.stringify(verdict(String(body.text))));
        else if (req.url === "/v1/extension/me")
          res.end(
            JSON.stringify({
              user_id: "maria",
              team: "finance",
              shadow_mode: false,
              incidents_url: "http://localhost:3000/security/history?user=maria",
            }),
          );
        else res.end(JSON.stringify({ status: "recorded" }));
      });
    }).listen(PORT, ok);
  });
}
const stopBrain = () => new Promise<void>((ok) => (server ? server.close(() => ok()) : ok()));

async function launch(): Promise<{ context: BrowserContext; page: Page }> {
  const context = await chromium.launchPersistentContext("", {
    channel: "chromium",
    args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`],
  });
  const worker = context.serviceWorkers()[0] ?? (await context.waitForEvent("serviceworker"));
  await worker.evaluate(
    (port) => chrome.storage.local.set({ key: "sk-test", brainUrl: `http://localhost:${port}` }),
    PORT,
  );
  await context.route("https://chatgpt.com/**", (r) =>
    r.fulfill({ contentType: "text/html", body: FIXTURE }),
  );
  const page = await context.newPage();
  await page.goto("https://chatgpt.com/");
  return { context, page };
}

const paste = (page: Page, text: string) =>
  page.evaluate((t) => {
    const el = document.getElementById("prompt-textarea")!;
    el.focus();
    const dt = new DataTransfer();
    dt.setData("text/plain", t);
    el.dispatchEvent(
      new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }),
    );
  }, text);

let context: BrowserContext;
let page: Page;
const composer = () => page.locator("#prompt-textarea");
const sent = () => page.getByTestId("sent");

test.beforeEach(async () => {
  calls = [];
  shadow = false;
  await startBrain();
  ({ context, page } = await launch());
});
test.afterEach(async () => {
  await context.close();
  await stopBrain();
});

test("paste is masked before it reaches the composer", async () => {
  await paste(page, `Pay ${IBAN} today`);
  await expect(composer()).toHaveText("Pay [IBAN_1] today");
  await expect(page.getByText("Masked before sending")).toBeVisible();
  await expect(page.getByText("Replaced: IBAN")).toBeVisible();
  expect(calls[0].auth).toBe("Bearer sk-test");
  expect(calls[0].body).toEqual({ text: `Pay ${IBAN} today`, model: "ChatGPT (personal)" }); // no user or team from the client
});

test("clean text is pasted and sent untouched", async () => {
  await paste(page, "Hello there");
  await expect(composer()).toHaveText("Hello there");
  await composer().press("Enter");
  await expect(sent()).toHaveText("Hello there");
});

test("submit with Enter is stopped on block and offers Company AI", async () => {
  await composer().click();
  await page.keyboard.type("SECRET salary table");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Not sent")).toBeVisible();
  await expect(page.getByRole("link", { name: "Use Company AI" })).toHaveAttribute(
    "href",
    "http://localhost:3000/chat",
  );
  await expect(sent()).toHaveCount(0);
  await expect(composer()).toHaveText("SECRET salary table");
});

test("the send button is checked too", async () => {
  await composer().click();
  await page.keyboard.type("SECRET again");
  await page.getByTestId("send-button").click();
  await expect(page.getByText("Not sent")).toBeVisible();
  await expect(sent()).toHaveCount(0);
});

test("warn holds the message until Send anyway, and records the acknowledgement", async () => {
  await composer().click();
  await page.keyboard.type("CARD number inside");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Check before sending")).toBeVisible();
  await expect(sent()).toHaveCount(0);
  await page.getByRole("button", { name: "Send anyway" }).click();
  await expect(sent()).toHaveText("CARD number inside");
  expect(calls.some((c) => c.path === "/v1/extension/ack")).toBe(true);
});

test("submit with mask replaces the text and waits for a second send", async () => {
  await composer().click();
  await page.keyboard.type(`IBAN ${IBAN}`);
  await page.keyboard.press("Enter");
  await expect(composer()).toHaveText("IBAN [IBAN_1]");
  await expect(sent()).toHaveCount(0);
});

test("shadow mode never changes or stops anything", async () => {
  shadow = true;
  await composer().click();
  await page.keyboard.type("SECRET but shadow");
  await page.keyboard.press("Enter");
  await expect(sent()).toHaveText("SECRET but shadow");
  await expect(page.getByText("Not sent")).toHaveCount(0);
  await paste(page, `IBAN ${IBAN}`);
  await expect(composer()).toHaveText(`IBAN ${IBAN}`);
});

test("when the brain is down it fails open and shows the offline badge", async () => {
  await stopBrain();
  await composer().click();
  await page.keyboard.type("SECRET but offline");
  await page.keyboard.press("Enter");
  await expect(sent()).toHaveText("SECRET but offline");
  await expect(page.getByText("Pyli offline")).toBeVisible();
  await startBrain(); // so afterEach can close it
});

test("the card fits a 390 px phone", async () => {
  await page.setViewportSize({ width: 390, height: 800 });
  await composer().click();
  await page.keyboard.type("CARD number inside");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Check before sending")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
  const box = await page.getByRole("button", { name: "Send anyway" }).boundingBox();
  expect(box!.height).toBeGreaterThanOrEqual(44);
});
