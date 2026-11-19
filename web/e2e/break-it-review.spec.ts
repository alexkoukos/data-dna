import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { expect, test } from "@playwright/test";

// X28: a live miss on /break-it becomes an approved row in the eval set, and `make eval` lists it
// under "found live". Needs `make up` (the brain writes the file through the writable data/eval
// mount). The test puts the CSV and the eval report back the way they were.

const REPO = new URL("../../", import.meta.url).pathname;
const CSV = `${REPO}data/eval/attacks_scripts.csv`;
const REPORTS = [`${REPO}eval/report.md`, `${REPO}eval/report.json`];

test("a miss goes from /break-it to the review queue to the eval file to make eval", async ({
  page,
}) => {
  test.setTimeout(240_000);
  const before = readFileSync(CSV, "utf8");
  const reports = REPORTS.map((p) => (existsSync(p) ? readFileSync(p, "utf8") : null));
  // Letters only: a long run of digits can look like a phone number to the checks.
  const tag = Array.from(String(Date.now()), (d) => "abcdefghij"[Number(d)]).join("");
  const text = `please summarise the minutes of the quarterly review, run ${tag}`;
  try {
    await page.goto("/break-it");
    await page.getByLabel("Text to check").fill(text);
    await page.getByLabel(/Nickname/).fill("E2E breaker");
    await page.getByRole("button", { name: "Check it" }).click();
    await expect(page.getByText("Nothing caught this text")).toBeVisible();
    await expect(page.getByRole("region", { name: "Leaderboard" })).toContainText("Attempts today");

    await page.getByRole("button", { name: "It got through" }).click();
    await expect(page.getByText(/saves the exact text you typed/)).toBeVisible();
    await page.getByLabel("Warn").check();
    await page.getByLabel("Kind of trick").selectOption("spacing");
    await page.getByRole("button", { name: "Send this text as a test case" }).click();
    await expect(page.getByText(/review it before it joins/)).toBeVisible();

    await page.goto("/security/review");
    const row = page.getByRole("listitem").filter({ hasText: text });
    await expect(row.getByLabel("Submitted text")).toHaveText(text);
    await page.getByLabel(/Your name/).fill("e2e-reviewer");
    await row.getByRole("button", { name: "Approve" }).click();
    await expect(page.getByText(/now a row in the test set/)).toBeVisible();

    const added = readFileSync(CSV, "utf8")
      .split("\n")
      .filter((l) => l.includes("breakit"));
    expect(added.some((l) => l.includes("please summarise the minutes"))).toBe(true);

    // make eval exits 1 when a target fails; the report is still written.
    try {
      execFileSync("make", ["eval"], { cwd: REPO, stdio: "ignore", timeout: 200_000 });
    } catch {
      /* read the report below */
    }
    // CI's smoke job has no Python environment for `make eval`, so no report is written there.
    // The report line itself is also covered by a brain unit test.
    // The report is tracked in git now, so only check it when `make eval` actually rewrote it.
    const md = existsSync(`${REPO}eval/report.md`)
      ? readFileSync(`${REPO}eval/report.md`, "utf8")
      : null;
    if (md !== null && md !== reports[0]) {
      expect(md).toMatch(/Found live, still missed: \d+/);
      expect(md).toContain("source=breakit");
    } else {
      test.info().annotations.push({ type: "note", description: "make eval not available here" });
    }
  } finally {
    writeFileSync(CSV, before);
    REPORTS.forEach((p, i) => reports[i] !== null && writeFileSync(p, reports[i] as string));
  }
});
