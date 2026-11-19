import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("the landing page loads at / with the headline and both calls to action", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { level: 1, name: "Your data stays yours. Sentry holds the gate." }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "See the live demo" })).toHaveAttribute(
    "href",
    "/app",
  );
  await expect(page.getByRole("link", { name: "See how it works" })).toHaveAttribute(
    "href",
    "/how-it-works",
  );
});

test("the app home keeps the same navigation and lists every tool", async ({ page }) => {
  await page.goto("/app");
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav).toBeVisible();
  for (const name of ["How it works", "Security", "Developers", "Company AI"]) {
    await expect(nav.getByRole("link", { name })).toBeVisible();
  }
  await expect(page.getByRole("heading", { name: "Everything in the app" })).toBeVisible();
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
  ["/how-it-works", "The second after you paste."],
  ["/trust", "The gate is guarded too."],
  ["/developers", "Run it. Read it. Test it."],
] as const) {
  test(`${path} shows its headline, is reachable from the nav and has no axe violations`, async ({
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
