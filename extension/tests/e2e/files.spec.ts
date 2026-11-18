import { expect, test } from "./fixtures";

/** One-page PDFs made with pypdf, the same reader the server uses. */
const STAMPED = Buffer.from(
  "JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3ggWzAgMCA2MTIgNzkyXSAvQ29udGVudHMgNCAwIFIgL1Jlc291cmNlcyA8PCAvRm9udCA8PCAvRjEgNSAwIFIgPj4gPj4gPj4KZW5kb2JqCjQgMCBvYmoKPDwgL0xlbmd0aCA3MyA+PgpzdHJlYW0KQlQgL0YxIDEyIFRmIDcyIDcyMCBUZCAoQWtyeW9uIFN5c3RlbXMuIENsYXNzaWZpY2F0aW9uOiBSRVNUUklDVEVEKSBUaiBFVAplbmRzdHJlYW0KZW5kb2JqCjUgMCBvYmoKPDwgL1R5cGUgL0ZvbnQgL1N1YnR5cGUgL1R5cGUxIC9CYXNlRm9udCAvSGVsdmV0aWNhID4+CmVuZG9iagp4cmVmCjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA1OCAwMDAwMCBuIAowMDAwMDAwMTE1IDAwMDAwIG4gCjAwMDAwMDAyNDEgMDAwMDAgbiAKMDAwMDAwMDM2NCAwMDAwMCBuIAp0cmFpbGVyCjw8IC9TaXplIDYgL1Jvb3QgMSAwIFIgPj4Kc3RhcnR4cmVmCjQzNAolJUVPRg==",
  "base64",
); // "Akryon Systems. Classification: RESTRICTED"
const CLEAN = Buffer.from(
  "JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3ggWzAgMCA2MTIgNzkyXSAvQ29udGVudHMgNCAwIFIgL1Jlc291cmNlcyA8PCAvRm9udCA8PCAvRjEgNSAwIFIgPj4gPj4gPj4KZW5kb2JqCjQgMCBvYmoKPDwgL0xlbmd0aCA1MSA+PgpzdHJlYW0KQlQgL0YxIDEyIFRmIDcyIDcyMCBUZCAoVGVhbSBsdW5jaCBvbiBGcmlkYXkpIFRqIEVUCmVuZHN0cmVhbQplbmRvYmoKNSAwIG9iago8PCAvVHlwZSAvRm9udCAvU3VidHlwZSAvVHlwZTEgL0Jhc2VGb250IC9IZWx2ZXRpY2EgPj4KZW5kb2JqCnhyZWYKMCA2CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAwOSAwMDAwMCBuIAowMDAwMDAwMDU4IDAwMDAwIG4gCjAwMDAwMDAxMTUgMDAwMDAgbiAKMDAwMDAwMDI0MSAwMDAwMCBuIAowMDAwMDAwMzQyIDAwMDAwIG4gCnRyYWlsZXIKPDwgL1NpemUgNiAvUm9vdCAxIDAgUiA+PgpzdGFydHhyZWYKNDEyCiUlRU9G",
  "base64",
); // "Team lunch on Friday"

async function withFileInput(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.id = "pick";
    document.body.append(input);
    (window as unknown as { landed: string[] }).landed = [];
    input.addEventListener("change", () => {
      (window as unknown as { landed: string[] }).landed.push(
        ...[...input.files!].map((f) => f.name),
      );
    });
  });
}
const landed = (page: import("@playwright/test").Page) =>
  page.evaluate(() => (window as unknown as { landed: string[] }).landed);

test("a file stamped RESTRICTED is held back, removed, and says why", async ({ context }) => {
  const page = await context.newPage();
  await withFileInput(page);
  await page
    .locator("#pick")
    .setInputFiles({ name: "report.pdf", mimeType: "application/pdf", buffer: STAMPED });
  const card = page.getByRole("alertdialog");
  await expect(card).toContainText("File not attached");
  await expect(card).toContainText("marked RESTRICTED");
  await expect(page.locator("#pick")).toHaveValue("");
  expect(await landed(page)).toEqual([]); // the page never saw the file
});

test("a clean file goes through and says it was checked", async ({ context }) => {
  const page = await context.newPage();
  await withFileInput(page);
  await page
    .locator("#pick")
    .setInputFiles({ name: "lunch.pdf", mimeType: "application/pdf", buffer: CLEAN });
  await expect(page.getByText("Checked by Hive")).toBeVisible();
  await expect.poll(() => landed(page)).toEqual(["lunch.pdf"]);
});

test("a file copied in Finder and pasted is checked even though its name is on the clipboard as text", async ({
  context,
}) => {
  const page = await context.newPage();
  await page.goto("/");
  await page.evaluate(
    (bytes) => {
      const dt = new DataTransfer();
      dt.items.add(new File([new Uint8Array(bytes)], "report.pdf", { type: "application/pdf" }));
      dt.setData("text/plain", "report.pdf");
      document
        .querySelector("#prompt")!
        .dispatchEvent(
          new ClipboardEvent("paste", { bubbles: true, cancelable: true, clipboardData: dt }),
        );
    },
    [...STAMPED],
  );
  await expect(page.getByRole("alertdialog")).toContainText("File not attached");
});

test("a file the server cannot read makes Hive ask, it does not pass silently", async ({
  context,
}) => {
  const page = await context.newPage();
  await withFileInput(page);
  await page.locator("#pick").setInputFiles({
    name: "scan.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 junk"),
  });
  await expect(page.getByRole("alertdialog")).toContainText("could not read");
  expect(await landed(page)).toEqual([]);
});
