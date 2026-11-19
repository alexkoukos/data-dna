import { describe, expect, it } from "vitest";
import { companyChatUrl, DEFAULT_COMPANY_CHAT } from "../src/handoff";

describe("Company Chat hand-off for a stopped file", () => {
  it("adds the tool and the file name to the server's address", () => {
    const url = new URL(companyChatUrl("https://ai.example.test/chat", "ChatGPT", "q4 report.pdf"));
    expect(url.origin + url.pathname).toBe("https://ai.example.test/chat");
    expect(url.searchParams.get("from")).toBe("chatgpt");
    expect(url.searchParams.get("file")).toBe("q4 report.pdf");
  });

  it("falls back to the local stack for a missing or non-web address", () => {
    for (const base of [undefined, "", "javascript:alert(1)", "not a url"])
      expect(companyChatUrl(base, "Gemini", "a.pdf")).toBe(
        `${DEFAULT_COMPANY_CHAT}?from=gemini&file=a.pdf`,
      );
  });

  it("drops the server address's own query and caps long names", () => {
    const url = new URL(
      companyChatUrl("http://localhost:3000/chat?x=1#top", "Claude.ai", "n".repeat(500)),
    );
    expect(url.searchParams.get("x")).toBeNull();
    expect(url.hash).toBe("");
    expect(url.searchParams.get("file")).toHaveLength(120);
  });
});
