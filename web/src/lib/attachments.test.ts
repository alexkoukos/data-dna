import { describe, expect, it } from "vitest";
import {
  composeMessage,
  DEFAULT_LIMITS,
  fileSummary,
  precheck,
  safeName,
  typeNames,
  uploadHint,
} from "./attachments";

const f = (name: string, size: number) => new File(["x".repeat(size)], name);

describe("attachments", () => {
  it("puts each file after the question in the shape the brain reads back", () => {
    const msg = composeMessage("  Summarise  ", [
      { name: "a.pdf", text: "alpha", chars: 5, truncated: false },
      { name: "b].txt", text: "beta", chars: 9000, truncated: true },
    ]);
    expect(msg).toBe(
      "Summarise\n\n[File: a.pdf]\nalpha\n[End of file: a.pdf]\n\n" +
        "[File: b_.txt]\nbeta\n[Only the first 4 of 9,000 characters of this file were included.]\n[End of file: b_.txt]",
    );
    expect(composeMessage("", [{ name: "a.md", text: "x", chars: 1, truncated: false }])).toMatch(
      /^\[File: a\.md\]/,
    );
  });

  it("checks type, size, emptiness and count before uploading", () => {
    const L = { ...DEFAULT_LIMITS, maxBytes: 100, maxFiles: 1 };
    expect(precheck(f("a.pdf", 10), L, 0)).toBeNull();
    expect(precheck(f("a.PDF", 10), L, 0)).toBeNull();
    expect(precheck(f("a.png", 10), L, 0)).toMatch(/Attach a PDF/);
    expect(precheck(f("a.txt", 101), L, 0)).toMatch(/larger than 1 KB/);
    expect(precheck(f("a.txt", 0), L, 0)).toMatch(/empty/);
    expect(precheck(f("a.txt", 5), L, 1)).toMatch(/up to 1 file to/);
  });

  it("keeps file names safe for the message header", () => {
    expect(safeName("x\n]y")).toBe("x__y");
    expect(safeName("")).toBe("file");
    expect(safeName("a".repeat(300))).toHaveLength(200);
  });

  it("reads the extension's hand-off from the address", () => {
    expect(uploadHint("?from=chatgpt&file=q4.pdf")).toEqual({ tool: "ChatGPT", file: "q4.pdf" });
    expect(uploadHint("?file=q4.pdf")).toEqual({ tool: "an outside AI tool", file: "q4.pdf" });
    expect(uploadHint("?from=chatgpt")).toBeNull();
  });

  it("summarises file names for the outcome chip", () => {
    expect(fileSummary([{ name: "a.pdf" }])).toBe("a.pdf");
    expect(fileSummary([{ name: "a.pdf" }, { name: "b.pdf" }, { name: "c" }])).toBe(
      "a.pdf +2 more",
    );
  });
});

describe("accepted types in words", () => {
  it("lists images only when the server reads them", () => {
    expect(typeNames(DEFAULT_LIMITS.types)).toBe("PDF, Word (.docx), text, Markdown or CSV");
    expect(typeNames([...DEFAULT_LIMITS.types, ".png", ".jpg"])).toBe(
      "PDF, Word (.docx), text, Markdown, CSV or image (PNG, JPG)",
    );
  });
});
