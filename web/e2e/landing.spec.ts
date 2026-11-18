import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const loop = (page: import("@playwright/test").Page) => page.getByTestId("hero-loop");

test("the landing page loads at / with the headline and both calls to action", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { level: 1, name: "Your data is the honey. We guard the gate." }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "See the live demo" })).toHaveAttribute(
    "href",
    "/app",
  );
  await expect(page.getByRole("link", { name: "Read the deep dive" })).toBeVisible();
  await expect(loop(page)).toBeVisible();
});

test("the old home page still works at /app", async ({ page }) => {
  await page.goto("/app");
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Get the extension" }),
  ).toBeVisible();
});

test("picking a kind of data shows what is pasted and what leaves", async ({ page }) => {
  await page.goto("/");
  const section = page.locator("#catches");
  await section.getByRole("button", { name: "IBAN" }).click();
  await expect(section.getByRole("button", { name: "IBAN" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(section.getByText("[IBAN_1]")).toBeVisible();
  await expect(section.locator(".catch-foot .chip")).toContainText("Blocked");
  await section.getByRole("button", { name: "Source code" }).click();
  await expect(section.locator(".catch-foot .chip")).toContainText("Warned");
});

test.describe("with motion", () => {
  test.use({ reducedMotion: "no-preference" });

  test("the loop advances through all four scenes and starts over", async ({ page }) => {
    await page.clock.install();
    await page.goto("/");
    await expect(loop(page)).toHaveAttribute("data-mode", "loop");
    const seen: string[] = [];
    for (let ms = 0; ms <= 25_000; ms += 100) {
      const scene = await loop(page).getAttribute("data-scene");
      if (scene !== null && seen.at(-1) !== scene) seen.push(scene);
      await page.clock.runFor(100);
      await page.waitForTimeout(5);
    }
    expect(seen.slice(0, 5)).toEqual(["0", "1", "2", "3", "0"]);
  });

  test("the bee card appears in every scene", async ({ page }) => {
    await page.clock.install();
    await page.goto("/");
    const cards: string[] = [];
    for (let ms = 0; ms < 24_000; ms += 100) {
      const card = loop(page).locator(".bee-card-wrap.is-in .bee-card-head");
      if (await card.count()) {
        const text = (await card.first().textContent()) ?? "";
        if (cards.at(-1) !== text) cards.push(text);
      }
      await page.clock.runFor(100);
      await page.waitForTimeout(5);
    }
    expect(cards).toEqual([
      "That's hive honey. I kept it in.",
      "Bank details stay in the hive.",
      "Keys never leave the hive.",
      "Answered by Company AI.",
    ]);
  });

  test("the loop stops when the pause button is pressed", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Pause" }).click();
    await expect(loop(page)).toHaveAttribute("data-playing", "false");
  });
});

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("shows the scenes as still frames with a Next button, and nothing moves on its own", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(loop(page)).toHaveAttribute("data-mode", "static");
    await expect(page.getByRole("button", { name: "Pause" })).toHaveCount(0);
    const captions = [];
    for (let i = 0; i < 4; i++) {
      captions.push(await page.getByTestId("loop-caption").textContent());
      await expect(loop(page).locator(".bee-card-wrap.is-in")).toHaveCount(1);
      await page.getByRole("button", { name: "Next" }).click();
    }
    expect(new Set(captions).size).toBe(4);
    await page.waitForTimeout(1500);
    await expect(loop(page)).toHaveAttribute("data-scene", "0");
  });
});

for (const vp of [
  { name: "desktop", width: 1280, height: 800 },
  { name: "phone", width: 390, height: 800 },
]) {
  test(`landing on ${vp.name}: accessible and no sideways scroll`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).analyze();
    expect(
      results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? "")),
    ).toEqual([]);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth),
    ).toBe(false);
  });
}

for (const [path, h1] of [
  ["/how-it-works", "What happens in the second after you paste."],
  ["/trust", "The gate is guarded too."],
  ["/developers", "Run it, read it, test it."],
] as const) {
  test(`${path} shows its headline, is reachable from the header and has no axe violations`, async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByRole("navigation", { name: "Main" }).locator(`a[href="${path}"]`).click();
    await expect(page).toHaveURL(path);
    await expect(page.getByRole("heading", { level: 1, name: h1 })).toBeVisible();
    const r = await new AxeBuilder({ page }).analyze();
    expect(r.violations).toEqual([]);
  });
}
