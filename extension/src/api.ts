import { DEFAULT_POLICY, type Policy } from "./detect/policy";
import { getPolicy, getSettings, savePolicy } from "./storage";
import type { CheckResult } from "./types";

async function headers(): Promise<Record<string, string>> {
  const s = await getSettings();
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (s.token) h.Authorization = `Bearer ${s.token}`;
  else if (s.demoUser) h["X-Demo-User"] = s.demoUser;
  return h;
}

/** Same limit as the brain (MAX_INSPECT_CHARS). Longer text is refused here, never sent. */
export const MAX_CHARS = 100_000;
const MAX_ATTACHMENT_B64 = 20_000_000;

/**
 * The server address must be https, or http on this machine only. The token is a bearer token:
 * it never travels over plain http to another host, and a malformed address is refused.
 */
export function safeBrainUrl(raw: string): string | null {
  try {
    const u = new URL(raw);
    const local = ["localhost", "127.0.0.1", "[::1]"].includes(u.hostname);
    if (u.protocol !== "https:" && !(u.protocol === "http:" && local)) return null;
    if (u.username || u.password) return null;
    return u.origin;
  } catch {
    return null;
  }
}

/** Only the page and its path leave the browser: no query string, no fragment, no login part. */
export function cleanPageUrl(raw: string): string {
  try {
    const u = new URL(raw);
    return `${u.origin}${u.pathname}`;
  } catch {
    return "";
  }
}

async function url(path: string): Promise<string> {
  const base = safeBrainUrl((await getSettings()).brainUrl);
  if (!base) throw new Error("brain url refused");
  return `${base}${path}`;
}

interface CheckOut {
  action: CheckResult["action"];
  reasons: string[];
  findings: { entity: string; category: string; masked_preview: string }[];
  masked_text?: string | null;
  placeholders?: Record<string, string> | null;
  rewrite?: string | null;
  document?: CheckResult["document"] | null;
  alternative?: string | null;
  policy_version?: number;
}

/** L2. Returns null on any failure, so the caller can fall back to the fail mode. */
export async function checkRemote(
  text: string,
  tool: string,
  pageUrl: string,
  attachments: { filename: string; content_base64: string }[] = [],
): Promise<Partial<CheckResult> | null> {
  // Too long or too big to read: not sent. The caller treats null as "could not check" and fails closed.
  if (text.length > MAX_CHARS) return null;
  if (attachments.some((a) => a.content_base64.length > MAX_ATTACHMENT_B64)) return null;
  try {
    const res = await fetch(await url("/v1/check"), {
      method: "POST",
      headers: await headers(),
      body: JSON.stringify({ text, tool, url: cleanPageUrl(pageUrl), attachments }),
    });
    if (!res.ok) return null;
    const d = (await res.json()) as CheckOut;
    return {
      action: d.action,
      reasons: d.reasons,
      findings: d.findings.map((f) => ({
        entity: f.entity,
        category: f.category,
        preview: f.masked_preview,
      })),
      maskedText: d.masked_text ?? undefined,
      placeholders: d.placeholders ?? undefined,
      rewrite: d.rewrite ?? undefined,
      document: d.document ?? undefined,
      alternative: d.alternative ?? undefined,
      policyVersion: d.policy_version,
    };
  } catch {
    return null;
  }
}

export async function refreshPolicy(): Promise<Policy> {
  const current = await getPolicy();
  try {
    const h = await headers();
    if (current.etag) h["If-None-Match"] = current.etag;
    const res = await fetch(await url("/v1/policy"), { headers: h });
    if (res.status === 304) return current;
    if (!res.ok) return current;
    const body = (await res.json()) as Policy;
    const next = { ...DEFAULT_POLICY, ...body, etag: res.headers.get("ETag") ?? undefined };
    await savePolicy(next);
    return next;
  } catch {
    return current;
  }
}

export async function postEvents(events: unknown[]): Promise<boolean> {
  try {
    const res = await fetch(await url("/v1/events"), {
      method: "POST",
      headers: await headers(),
      body: JSON.stringify({ events }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function askLocal(
  prompt: string,
): Promise<{ answer: string; ready: boolean; model?: string }> {
  try {
    const res = await fetch(await url("/v1/ask-local"), {
      method: "POST",
      headers: await headers(),
      body: JSON.stringify({ prompt }),
    });
    if (!res.ok) return { answer: "", ready: false };
    return (await res.json()) as { answer: string; ready: boolean; model?: string };
  } catch {
    return { answer: "", ready: false };
  }
}

export async function pair(
  code: string,
): Promise<{ token: string; user: string; team: string } | null> {
  try {
    const res = await fetch(await url("/v1/pair"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (!res.ok) return null;
    return (await res.json()) as { token: string; user: string; team: string };
  } catch {
    return null;
  }
}
