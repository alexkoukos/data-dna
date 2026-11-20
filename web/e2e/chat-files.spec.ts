import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// Company Chat file upload against the full stack (`make up`): the brain reads the file, the
// gateway checks the message, the demo model answers. All files are synthetic.

const IBAN = "GR1601101250000000012300695";

/** A one-page PDF with real text, built by hand (same as the brain's test helper). */
function pdfWithText(text: string): Buffer {
  const stream = `BT /F1 12 Tf 72 720 Td (${text}) Tj ET`;
  const objs = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((body, i) => {
    offsets.push(out.length);
    out += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = out.length;
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const off of offsets) out += `${String(off).padStart(10, "0")} 00000 n \n`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return Buffer.from(out, "latin1");
}

// The composer's picker. With the hand-off banner open, the banner has its own picker first.
const composerInput = (page: Page) => page.locator('input[type="file"]').last();

async function seriousViolations(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  return results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
}

test("a file with an IBAN is masked, answered, and the outcome names the file", async ({
  page,
}) => {
  await page.goto("/chat");
  await composerInput(page).setInputFiles({
    name: "pay.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(`Please pay invoice 42 to ${IBAN} by Friday.`),
  });
  await expect(page.getByText("· Ready")).toBeVisible();
  await page.getByRole("textbox", { name: "Your question" }).fill("What does this file ask?");
  await page.getByRole("button", { name: "Send" }).click();
  // The outcome chip says the outcome in words and names the file.
  await expect(page.getByText(/^Masked\s*· pay\.txt$/)).toBeVisible({ timeout: 30_000 });
  // The file text is never kept in the browser's saved chats.
  const saved = await page.evaluate(() => localStorage.getItem("sentry.chats") ?? "");
  expect(saved).toContain("pay.txt");
  expect(saved).not.toContain(IBAN);
  // The composer under the conversation takes files too.
  await expect(page.getByRole("button", { name: "Attach files" })).toBeVisible();
});

test("a clean PDF is allowed and can be sent with no typed question", async ({ page }) => {
  await page.goto("/chat");
  await composerInput(page).setInputFiles({
    name: "lunch.pdf",
    mimeType: "application/pdf",
    buffer: pdfWithText("Team lunch on Friday at noon"),
  });
  await expect(page.getByText("· Ready")).toBeVisible();
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/^Allowed\s*· lunch\.pdf$/)).toBeVisible({ timeout: 30_000 });
});

test("a renamed file is refused in plain words", async ({ page }) => {
  await page.goto("/chat");
  await composerInput(page).setInputFiles({
    name: "fake.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("MZ this is not a PDF"),
  });
  await expect(page.getByRole("alert")).toContainText("fake.pdf");
  await expect(page.getByRole("alert")).toContainText("not a PDF");
});

for (const vp of [
  { name: "desktop", width: 1280, height: 800 },
  { name: "phone 390 px", width: 390, height: 800 },
]) {
  test(`/chat with an attachment and the hand-off banner on ${vp.name}: accessible`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto("/chat?from=chatgpt&file=q4-report.pdf");
    await expect(page.getByRole("region", { name: "Upload the file here instead" })).toContainText(
      "You tried to upload q4-report.pdf to ChatGPT.",
    );
    expect(await seriousViolations(page)).toEqual([]); // with the banner open
    await composerInput(page).setInputFiles({
      name: "notes.md",
      mimeType: "text/markdown",
      buffer: Buffer.from("# Notes\nNothing sensitive here."),
    });
    await expect(page.getByText("· Ready")).toBeVisible();
    // Attaching a file closes the banner: it has done its job.
    await expect(page.getByRole("region", { name: "Upload the file here instead" })).toBeHidden();
    await page.waitForLoadState("networkidle");
    expect(await seriousViolations(page)).toEqual([]);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(overflow).toBe(false);
    const small = await page.evaluate(() =>
      [
        ...document.querySelectorAll<HTMLElement>(
          '[aria-label="Upload the file here instead"] button, [aria-label="Attached files"] button, button[aria-label="Attach files"], button[aria-label="Send"]',
        ),
      ]
        .filter((el) => el.offsetParent !== null)
        .map((el) => ({ el: el.outerHTML.slice(0, 80), h: el.getBoundingClientRect().height }))
        .filter((x) => x.h < 44),
    );
    expect(small).toEqual([]);
  });
}
