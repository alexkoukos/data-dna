import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { sendChat, type Identity } from "./chatApi";

const stale: Identity = { userId: "demo-old", team: "general", key: "sk-old", model: "demo-mock" };

describe("sendChat with a stale key", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());

  it("gets a new key and sends the message once more instead of asking for a reload", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const headers = (init?.headers ?? {}) as Record<string, string>;
        calls.push(`${url} ${headers.Authorization ?? ""}`);
        if (url === "/api/v1/keys")
          return new Response(JSON.stringify({ key: "sk-new", default_model: "demo-mock" }), {
            status: 201,
          });
        const auth = headers.Authorization;
        return auth === "Bearer sk-old"
          ? new Response("{}", { status: 401 })
          : new Response(JSON.stringify({ choices: [{ message: { content: "hello" } }] }), {
              status: 200,
            });
      }),
    );
    const res = await sendChat(stale, [{ role: "user", content: "hi" }]);
    expect(res).toMatchObject({ kind: "answer", text: "hello" });
    expect(stale.key).toBe("sk-new"); // the same object is updated, so the next message uses it
    expect(calls).toHaveLength(3);
  });

  it("does not loop when the new key is refused too", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        url === "/api/v1/keys"
          ? new Response(JSON.stringify({ key: "sk-new", default_model: "demo-mock" }), {
              status: 201,
            })
          : new Response("{}", { status: 401 }),
      ),
    );
    const res = await sendChat({ ...stale }, [{ role: "user", content: "hi" }]);
    expect(res.kind).toBe("error");
  });
});
