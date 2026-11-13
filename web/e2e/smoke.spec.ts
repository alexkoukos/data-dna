import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const ROUTES = [
  "/",
  "/chat",
  "/connect",
  "/security",
  "/security/tools",
  "/security/incidents",
  "/security/documents",
  "/security/policies",
  "/security/ask",
];
const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 800 },
  { name: "phone 390 px", width: 390, height: 800 },
];

async function seriousViolations(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  return results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
}

// W6: every route is accessible, fits a 390 px phone and has touch targets of at least 44 px.
for (const vp of VIEWPORTS) {
  for (const path of ROUTES) {
    test(`${path} on ${vp.name}: accessible, no sideways scroll, big touch targets`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(path);
      await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
      await page.waitForLoadState("networkidle");
      expect(await seriousViolations(page)).toEqual([]);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth,
      );
      expect(overflow).toBe(false);
      const small = await page.evaluate(() =>
        [...document.querySelectorAll<HTMLElement>("button, nav a, select, textarea, input")]
          .filter((el) => el.offsetParent !== null)
          .map((el) => ({ el: el.outerHTML.slice(0, 80), h: el.getBoundingClientRect().height }))
          .filter((x) => x.h < 44),
      );
      expect(small).toEqual([]);
    });
  }
}

test("security overview shows the demo company and links to incidents", async ({ page }) => {
  await page.goto("/security");
  await expect(page.getByText("Prompts checked")).toBeVisible();
  await expect(page.getByText("Demo data")).toBeVisible();
  await page.getByRole("link", { name: /Review all/ }).click();
  await expect(page.getByRole("heading", { name: "Security" })).toBeVisible();
  await expect(page.getByText(/newest first/)).toBeVisible();
});

test("AI tools lists unapproved tools first and can filter", async ({ page }) => {
  await page.goto("/security/tools");
  await expect(page.getByRole("heading", { level: 3 }).first()).toBeVisible();
  await page.getByRole("button", { name: /^Approved/ }).click();
  await expect(page.getByText("Unapproved", { exact: true })).toHaveCount(0);
});

test("chat masks a bank account number and still answers", async ({ page }) => {
  await page.goto("/chat");
  await page.getByRole("button", { name: "Try a bank account number" }).click();
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Masked")).toBeVisible();
  await expect(page.getByText(/passed the safety check/)).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? "")),
  ).toEqual([]);
});

test("chat holds a risky message and asks before sending", async ({ page }) => {
  await page.goto("/chat");
  await page
    .getByLabel("Message")
    .fill("AMKA 01011990123 card 4111 1111 1111 1111 IBAN GR1601101250000000012300695");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Check before this goes out")).toBeVisible();
  await page.getByLabel(/Say why/).fill("needed for an audit");
  await page.getByRole("button", { name: "Send anyway" }).click();
  await expect(page.getByText(/passed the safety check/)).toBeVisible();
});

test("policies: change one, see it saved, then put it back", async ({ page }) => {
  await page.goto("/security/policies");
  const select = page.getByLabel("What happens to client names");
  const original = await select.inputValue();
  const other = original === "block" ? "warn" : "block";
  try {
    await select.selectOption(other);
    await page.getByRole("button", { name: "Save client names" }).click();
    await expect(page.getByText(/Last changed by dashboard/).first()).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("What happens to client names")).toHaveValue(other);
  } finally {
    await page.request.put("http://localhost:8001/v1/policies", {
      data: { scope: "category", key: "client_name", action: original, updated_by: "e2e" },
    });
  }
});

test("connect page turns to Connected after a real request with the shown key", async ({
  page,
}) => {
  await page.goto("/connect");
  await expect(page.getByText(/Waiting for first request/)).toBeVisible();
  await page.getByRole("button", { name: "Show personal key" }).click();
  const key = await page.getByRole("textbox", { name: "Personal key" }).inputValue();
  const res = await page.request.post("http://localhost:4000/v1/chat/completions", {
    headers: { Authorization: `Bearer ${key}` },
    data: { model: "demo-mock", messages: [{ role: "user", content: "Hello" }] },
  });
  expect(res.ok()).toBe(true);
  await expect(page.getByText(/Connected\. The gateway has checked/)).toBeVisible({
    timeout: 10_000,
  });
});

test("ask: a preset question shows a table and the SQL", async ({ page }) => {
  await page.goto("/security/ask");
  await page.getByRole("button", { name: /Which AI tools are used most/ }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await page.getByText("Show the SQL behind this answer").click();
  await expect(page.getByLabel("SQL for this answer")).toContainText("SELECT");
});

test("incident detail: the name stays sealed until a second person approves", async ({ page }) => {
  // Earlier runs leave reveal requests behind, so pick an incident that has none yet.
  const list = await (
    await page.request.get("http://localhost:8001/v1/incidents?limit=100")
  ).json();
  let fresh: number | null = null;
  for (const item of list.items as { id: number }[]) {
    const d = await (
      await page.request.get(`http://localhost:8001/v1/incidents/${item.id}`)
    ).json();
    if (d.reveals.length === 0) {
      fresh = item.id;
      break;
    }
  }
  expect(fresh, "an incident without a reveal request (run make reset)").not.toBeNull();
  await page.goto(`/security/incidents/${fresh}`);
  await expect(page.getByText("What happened")).toBeVisible();
  await expect(page.getByText(/real name stays sealed/)).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? "")),
  ).toEqual([]);

  await page.getByLabel("Your name").fill("Anna");
  await page.getByLabel(/Why do you need/).fill("Pasted a client contract into a chat");
  await page.getByRole("button", { name: "Request reveal" }).click();
  await expect(page.getByText(/Waiting for a second person/)).toBeVisible();

  await page.getByLabel("Your name").fill("Anna");
  await page.getByRole("button", { name: "Approve the reveal" }).click();
  await expect(page.getByRole("alert")).toContainText("second person");

  await page.getByLabel("Your name").fill("Nikos");
  await page.getByRole("button", { name: "Approve the reveal" }).click();
  await expect(page.getByText(/Approved by Nikos/)).toBeVisible();
  await page.getByLabel("Your name").fill("Anna");
  await page.getByRole("button", { name: "Show the real name" }).click();
  await expect(page.getByText(/Real name: .+This view was logged/)).toBeVisible();
});
