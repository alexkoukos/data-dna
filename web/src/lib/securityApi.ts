export interface Metrics {
  prompts_checked: number;
  zero_llm_share: number | null;
  incidents_7d: number;
  incidents_prev_7d: number;
  unapproved_tools: number;
  demo_data: boolean;
  as_of: string | null;
}

export type Decision = "allow" | "mask" | "warn" | "local" | "block";

export interface Incident {
  id: number;
  ts: string;
  user: string;
  team: string | null;
  tool: string | null;
  decision: Decision;
  categories: string[];
  reasons: string[];
  masked_preview: string | null;
  score: number | null;
}

export interface IncidentPage {
  total: number;
  items: Incident[];
}

export interface Tool {
  id: number;
  name: string;
  vendor: string | null;
  category: string | null;
  approval: "approved" | "tolerated" | "unapproved";
  risk: "low" | "medium" | "high";
  reason: string | null;
  alternative: string | null;
  teams: string[];
  peak_users: number;
  requests: number;
  trend: number[];
  first_seen: string | null;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as T;
}

export const fetchMetrics = () => get<Metrics>("/v1/metrics");
export const fetchInventory = () => get<Tool[]>("/v1/inventory");
export const fetchIncidents = (decision: Decision | "all", offset: number, limit = 25) => {
  const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (decision !== "all") q.set("decision", decision);
  return get<IncidentPage>(`/v1/incidents?${q.toString()}`);
};
