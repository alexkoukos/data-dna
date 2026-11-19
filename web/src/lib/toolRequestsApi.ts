import { savedIdentity } from "./chatApi";

export interface ToolRequest {
  id: number;
  created_at: string;
  requester: string;
  team: string;
  tool: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
  decided_by: string | null;
  note: string | null;
  risk: "low" | "medium" | "high" | null;
  allowed_categories: string[] | null;
  alternative: string | null;
}

/** Categories security can allow for an approved tool. Same names as the policy page. */
export const CATEGORIES = [
  "greek_id",
  "iban",
  "card",
  "secret",
  "person_email_phone",
  "client_name",
  "source_code",
] as const;

async function problem(res: Response, fallback: string): Promise<Error> {
  const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
  return new Error(typeof body.detail === "string" ? body.detail : fallback);
}

export async function requestTool(body: {
  user_id: string;
  team: string;
  tool: string;
  reason: string;
}): Promise<ToolRequest> {
  const res = await fetch("/api/v1/tool-requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await problem(res, "We could not send your request. Try again in a moment.");
  return (await res.json()) as ToolRequest;
}

export async function fetchRequests(): Promise<ToolRequest[]> {
  const res = await fetch("/api/v1/tool-requests");
  if (!res.ok) throw new Error("The requests could not be loaded.");
  return (await res.json()) as ToolRequest[];
}

export async function decideRequest(
  id: number,
  body: {
    reviewer: string;
    approve: boolean;
    risk?: string;
    allowed_categories?: string[];
    alternative?: string;
    note?: string;
  },
): Promise<void> {
  const res = await fetch(`/api/v1/tool-requests/${id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await problem(res, "That could not be saved. Nothing was changed.");
}

/** Decisions on this person's requests that they have not seen. Each is returned once. */
export async function collectOutcomes(userId: string): Promise<ToolRequest[]> {
  try {
    const saved = savedIdentity();
    const res = await fetch(`/api/v1/users/${encodeURIComponent(userId)}/tool-request-outcomes`, {
      method: "POST",
      headers: saved && saved.userId === userId ? { Authorization: `Bearer ${saved.key}` } : {},
    });
    return res.ok ? ((await res.json()) as ToolRequest[]) : [];
  } catch {
    return [];
  }
}

export function outcomeText(r: ToolRequest): string {
  if (r.status === "approved") {
    return `${r.tool} was approved${r.risk ? ` (risk: ${r.risk})` : ""}. You can use it${
      r.allowed_categories?.length ? ` with: ${r.allowed_categories.join(", ")}` : ""
    }.`;
  }
  const alt = r.alternative ? ` Use ${r.alternative} instead.` : "";
  return `${r.tool} was not approved.${r.note ? ` ${r.note}` : ""}${alt}`;
}
