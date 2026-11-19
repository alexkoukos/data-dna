import { afterEach, describe, expect, it, vi } from "vitest";
import { detailText, requestReveal } from "./securityApi";

afterEach(() => vi.unstubAllGlobals());

describe("error text", () => {
  it("joins a pydantic 422 list instead of showing [object Object]", () => {
    expect(
      detailText([
        { type: "missing", loc: ["body", "title"], msg: "Field required" },
        { type: "x", msg: "Too short" },
      ]),
    ).toBe("Field required. Too short");
    expect(detailText("plain")).toBe("plain");
    expect(detailText(undefined)).toBe("");
  });

  it("a pydantic 422 list shows its messages, not [object Object]", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: [{ msg: "Field required" }] }), { status: 422 }),
      ),
    );
    await expect(requestReveal(1, "maria", "why")).rejects.toThrow("Field required");
  });
});
