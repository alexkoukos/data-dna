import { afterEach, describe, expect, it, vi } from "vitest";
import { collectOutcomes } from "./toolRequestsApi";

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

function stubFetch() {
  const fetchMock = vi.fn(async () => new Response("[]", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("collectOutcomes", () => {
  it("sends the saved key for the same person", async () => {
    window.localStorage.setItem(
      "dna.identity",
      JSON.stringify({ userId: "maria", team: "finance", key: "sk-maria", model: "demo-mock" }),
    );
    const fetchMock = stubFetch();
    await collectOutcomes("maria");
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.headers).toEqual({ Authorization: "Bearer sk-maria" });
  });

  it("sends no key for someone else and still returns an empty list", async () => {
    window.localStorage.setItem(
      "dna.identity",
      JSON.stringify({ userId: "maria", team: "finance", key: "sk-maria", model: "demo-mock" }),
    );
    const fetchMock = stubFetch();
    expect(await collectOutcomes("someone-else")).toEqual([]);
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.headers).toEqual({});
  });
});
