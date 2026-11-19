import { describe, expect, it } from "vitest";
import { cleanPageUrl, safeBrainUrl } from "../src/api";

describe("safeBrainUrl", () => {
  it("accepts https and http on this machine", () => {
    expect(safeBrainUrl("https://sentry.example.com/")).toBe("https://sentry.example.com");
    expect(safeBrainUrl("http://localhost:8001")).toBe("http://localhost:8001");
    expect(safeBrainUrl("http://127.0.0.1:8001/x")).toBe("http://127.0.0.1:8001");
  });
  it("refuses plain http to another host, other schemes, logins and junk", () => {
    for (const bad of [
      "http://sentry.example.com",
      "http://localhost.evil.com",
      "javascript:alert(1)",
      "ftp://x.test",
      "https://user:pw@x.test",
      "nope",
      "",
    ])
      expect(safeBrainUrl(bad)).toBeNull();
  });
});

describe("cleanPageUrl", () => {
  it("keeps the page and path only", () => {
    expect(cleanPageUrl("https://claude.ai/chat/abc?token=secret#frag")).toBe(
      "https://claude.ai/chat/abc",
    );
    expect(cleanPageUrl("not a url")).toBe("");
  });
});
