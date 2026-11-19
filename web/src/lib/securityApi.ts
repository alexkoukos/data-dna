export interface Metrics {
  prompts_checked: number;
  zero_llm_share: number | null;
  incidents_7d: number;
  incidents_prev_7d: number;
  unapproved_tools: number;
  demo_data: boolean;
  as_of: string | null;
}

export type Decision = "allow" | "mask" | "warn" | "local" | "block" | "rerouted";

export interface TraceStep {
  layer: string;
  fired: boolean;
  score: number | null;
  detail: string;
}

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
  shadow?: boolean;
  trace?: TraceStep[];
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
  /** Where we saw it: the browser extension, network logs, or both. */
  sources: ("extension" | "logs")[];
  allowed_categories?: string[];
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

/** Newest incidents first, up to `max`, read in pages of 100 (the most the server returns at once). */
export async function fetchRecentIncidents(max = 300): Promise<Incident[]> {
  const first = await fetchIncidents("all", 0, 100);
  const pages = Math.ceil(Math.min(first.total, max) / 100);
  const rest = await Promise.all(
    Array.from({ length: Math.max(0, pages - 1) }, (_, i) =>
      fetchIncidents("all", (i + 1) * 100, 100),
    ),
  );
  return [first, ...rest].flatMap((p) => p.items);
}

export interface Policy {
  scope: "category" | "sensitivity";
  key: string;
  action: Decision;
  updated_by: string | null;
  updated_at: string | null;
}

export interface DocumentRow {
  id: number;
  title: string;
  sensitivity: string;
  dna_enabled: boolean;
  created_at: string | null;
  incidents: number;
}

export const fetchPolicies = () => get<Policy[]>("/v1/policies");
export const fetchDocuments = () => get<DocumentRow[]>("/v1/documents");

/** Save one policy. Throws an Error whose message is safe to show. */
export async function savePolicy(
  scope: Policy["scope"],
  key: string,
  action: Decision,
): Promise<Policy> {
  let res: Response;
  try {
    res = await fetch("/api/v1/policies", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope, key, action, updated_by: "dashboard" }),
    });
  } catch {
    throw new Error("We could not reach the server. Check your connection and try again.");
  }
  if (!res.ok) {
    throw new Error("The change was not saved. Nothing was changed. Try again in a moment.");
  }
  return (await res.json()) as Policy;
}

export interface Preset {
  id: string;
  question: string;
}

export interface Answer {
  id: string;
  question: string;
  sql: string;
  parameters: Record<string, string>;
  columns: string[];
  rows: (string | number | null)[][];
}

export const fetchPresets = () => get<Preset[]>("/v1/ask/presets");

export async function askPreset(preset: string): Promise<Answer> {
  const res = await fetch("/api/v1/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset }),
  });
  if (!res.ok) throw new Error("We could not get the answer. Try again in a moment.");
  return (await res.json()) as Answer;
}

export interface Reveal {
  id: number;
  incident_id: number;
  requested_by: string;
  reason: string;
  approved_by: string | null;
  status: "pending" | "approved" | "denied";
  ts: string | null;
}

export interface IncidentDetail {
  incident: Incident;
  copy_code: string | null;
  document: { id: number; title: string; sensitivity: string } | null;
  timeline: Incident[];
  reveals: Reveal[];
}

export const fetchIncidentDetail = (id: string) => get<IncidentDetail>(`/v1/incidents/${id}`);

/** A FastAPI 422 sends a list of {msg} objects; a plain error sends a string. */
export function detailText(detail: unknown): string {
  if (Array.isArray(detail)) {
    return detail
      .map((d) =>
        d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : "",
      )
      .filter(Boolean)
      .join(". ");
  }
  return detail == null ? "" : String(detail);
}

async function send<T>(path: string, method: "POST" | "GET", body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error("We could not reach the server. Check your connection and try again.");
  }
  if (!res.ok) {
    let detail = "";
    try {
      detail = detailText(((await res.json()) as { detail?: unknown }).detail);
    } catch {
      // fall through to the generic message
    }
    throw new Error(
      res.status === 422 || res.status === 403 || res.status === 404
        ? detail || "That was not allowed."
        : "Something went wrong on our side. Nothing was changed. Try again in a moment.",
    );
  }
  return (await res.json()) as T;
}

export const requestReveal = (incident_id: number, requested_by: string, reason: string) =>
  send<Reveal>("/v1/reveal-requests", "POST", { incident_id, requested_by, reason });
export const decideReveal = (id: number, decided_by: string, approve: boolean) =>
  send<Reveal>(`/v1/reveal-requests/${id}/${approve ? "approve" : "deny"}`, "POST", {
    decided_by,
  });
export const fetchIdentity = (incident: number, request: number, viewer: string) =>
  send<{ pseudonym: string; display_name: string | null }>(
    `/v1/incidents/${incident}/identity?request_id=${request}&viewer=${encodeURIComponent(viewer)}`,
    "GET",
  );

export interface ProposedMark {
  position: number;
  variants: string[];
  preview: string;
}
export interface DnaState {
  enabled: boolean;
  marks: number;
  copies: string[];
}
export interface IssuedCopy {
  copy_code: string;
  recipient: string;
}

async function detail(res: Response, fallback: string): Promise<Error> {
  try {
    const d = ((await res.json()) as { detail?: unknown }).detail;
    if (typeof d === "string" && d) return new Error(d);
  } catch {
    // use the fallback
  }
  return new Error(fallback);
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`/api${path}`, { method: "POST", body: form });
  if (!res.ok) throw await detail(res, "That did not work. Nothing was changed. Try again.");
  return (await res.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await detail(res, "That did not work. Nothing was changed. Try again.");
  return (await res.json()) as T;
}

export const registerDocument = (form: FormData) =>
  postForm<{ id: number; title: string; sensitivity: string; chunks: number }>(
    "/v1/documents",
    form,
  );
export const proposeMarks = (id: number) =>
  postForm<{ marks: ProposedMark[] }>(`/v1/documents/${id}/dna/propose`, new FormData());
export const approveMarks = (id: number, marks: ProposedMark[]) =>
  postJson<DnaState>(`/v1/documents/${id}/dna/approve`, {
    marks: marks.map((m) => ({ position: m.position, variants: m.variants })),
  });
export const issueCopies = (id: number, recipients: string[]) =>
  postJson<IssuedCopy[]>(`/v1/documents/${id}/copies`, { recipients });
export const fetchDnaState = (id: number) => get<DnaState>(`/v1/documents/${id}/dna`);

export async function askFree(question: string): Promise<Answer> {
  const res = await fetch("/api/v1/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw await detail(res, "We could not get the answer. Try again in a moment.");
  return (await res.json()) as Answer;
}

export interface ShadowStatus {
  enabled: boolean;
  would_have: Partial<Record<Decision, number>>;
  total: number;
}

export const fetchShadow = () => get<ShadowStatus>("/v1/shadow-mode");

export async function saveShadow(enabled: boolean): Promise<ShadowStatus> {
  let res: Response;
  try {
    res = await fetch("/api/v1/shadow-mode", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled, updated_by: "dashboard" }),
    });
  } catch {
    throw new Error("We could not reach the server. Check your connection and try again.");
  }
  if (!res.ok) throw new Error("Shadow mode was not changed. Try again in a moment.");
  return (await res.json()) as ShadowStatus;
}

export const COMPLIANCE_REPORT_URL = "/api/v1/compliance-report.pdf";
export const COMPLIANCE_REPORT_HTML_URL = "/api/v1/compliance-report.html";

export interface PolicyPreview {
  days: number;
  incidents_checked: number;
  changed: number;
  stricter: number;
  looser: number;
  moves: { from: Decision; to: Decision; count: number }[];
}

export async function previewPolicy(
  scope: string,
  key: string,
  action: Decision,
): Promise<PolicyPreview> {
  let res: Response;
  try {
    res = await fetch("/api/v1/policies/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope, key, action }),
    });
  } catch {
    throw new Error("We could not reach the server. Check your connection and try again.");
  }
  if (!res.ok) throw new Error("The preview could not be made. Try again in a moment.");
  return (await res.json()) as PolicyPreview;
}

// ---- X13 policies per team and role -----------------------------------------------------------
export interface GroupPolicy {
  kind: "team" | "role";
  group: string;
  scope: "category" | "sensitivity";
  key: string;
  action: Decision;
}

export const fetchGroupPolicies = () => get<GroupPolicy[]>("/v1/policies/groups");

async function groupCall(method: "PUT" | "DELETE", p: GroupPolicy): Promise<GroupPolicy[]> {
  let res: Response;
  try {
    if (method === "PUT") {
      res = await fetch("/api/v1/policies/groups", {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...p, updated_by: "dashboard" }),
      });
    } else {
      const q = new URLSearchParams({
        kind: p.kind,
        group: p.group,
        scope: p.scope,
        key: p.key,
        updated_by: "dashboard",
      });
      res = await fetch(`/api/v1/policies/groups?${q.toString()}`, { method });
    }
  } catch {
    throw new Error("We could not reach the server. Check your connection and try again.");
  }
  if (!res.ok) {
    let detail = "";
    try {
      detail = detailText(((await res.json()) as { detail?: unknown }).detail);
    } catch {
      // generic message below
    }
    throw new Error(detail || "The change was not saved. Nothing was changed. Try again.");
  }
  return (await res.json()) as GroupPolicy[];
}

export const saveGroupPolicy = (p: GroupPolicy) => groupCall("PUT", p);
export const deleteGroupPolicy = (p: GroupPolicy) => groupCall("DELETE", p);

// ---- X18 ROI, X20 weekly summary, X19 coaching ------------------------------------------------
export interface Roi {
  days: number;
  leaks_stopped: number;
  would_have_stopped: number;
  by_category: Record<string, number>;
  exposure_eur: number;
  cost_avoided_eur: number;
  assumptions: {
    likelihood: number;
    unit_cost_eur: Record<string, number>;
    document_cost_eur: Record<string, number>;
    note: string;
  };
  tools: { name: string; approval: string; risk: string; requests: number; risk_score: number }[];
}

export interface WeeklySummary {
  headline: string;
  lines: string[];
  week: Record<string, number>;
  previous: Record<string, number>;
}

export interface CoachingStats {
  shown: number;
  accepted: number;
  acceptance_rate: number;
}

export const fetchRoi = () => get<Roi>("/v1/roi");
export const fetchWeekly = () => get<WeeklySummary>("/v1/weekly-summary");
export const fetchCoaching = () => get<CoachingStats>("/v1/coaching");

// ---- X24 history per person and per document --------------------------------------------------
export interface History {
  subject: string | null;
  found: boolean;
  total: number;
  by_decision: Record<string, number>;
  items: Incident[];
}

export const fetchUserHistory = (user: string) =>
  get<History>(`/v1/users/${encodeURIComponent(user)}/history`);
export const fetchDocumentHistory = (id: number) => get<History>(`/v1/documents/${id}/history`);
