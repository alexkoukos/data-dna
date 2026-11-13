import { vi } from "vitest";
import type { Incident, Metrics, Tool } from "../lib/securityApi";

export const metrics: Metrics = {
  prompts_checked: 9769,
  zero_llm_share: 0.896,
  incidents_7d: 329,
  incidents_prev_7d: 335,
  unapproved_tools: 4,
  demo_data: true,
  as_of: "2026-11-12T18:55:07Z",
};

export const incident = (id: number, over: Partial<Incident> = {}): Incident => ({
  id,
  ts: "2026-11-12T18:55:07Z",
  user: "u-de036ece",
  team: "Engineering",
  tool: "Claude Code (gateway)",
  decision: "mask",
  categories: ["secret"],
  reasons: ["Contains secret"],
  masked_preview: "AK••••••••••••••MPLE",
  score: 0.9,
  ...over,
});

export const tool = (id: number, over: Partial<Tool> = {}): Tool => ({
  id,
  name: `Tool ${id}`,
  vendor: "Vendor",
  category: "chat",
  approval: "unapproved",
  risk: "high",
  reason: "Keeps prompts",
  alternative: "Company AI",
  teams: ["Sales"],
  peak_users: 12,
  requests: 300,
  trend: [1, 2, 3, 4, 5, 6, 7],
  first_seen: "2026-10-31",
  ...over,
});

/** Answer fetch calls by URL prefix. A value of "fail" makes the call return a 500. */
export function mockApi(routes: Record<string, unknown | "fail" | ((url: string) => unknown)>) {
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const key = Object.keys(routes).find((k) => url.includes(k));
    const value = key ? routes[key] : "fail";
    const body = typeof value === "function" ? (value as (u: string) => unknown)(url) : value;
    if (body === "fail") return new Response("{}", { status: 500 });
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}
