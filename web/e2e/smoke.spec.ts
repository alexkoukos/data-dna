import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const path of ["/", "/chat", "/connect", "/security"]) {
  test(`${path} loads and has no serious accessibility issues`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    );
    expect(serious).toEqual([]);
  });
}

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
