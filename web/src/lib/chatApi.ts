import type { Outcome } from "../components/OutcomeChip";

export interface Identity {
  userId: string;
  team: string;
  key: string;
  model: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export type ChatResult =
  | { kind: "answer"; text: string; outcome: Outcome; reasons: string[] }
  | { kind: "warn"; reasons: string[] }
  | { kind: "block"; reasons: string[]; alternative: string }
  | { kind: "error"; message: string };

const STORAGE_KEY = "dna.identity";

function readStored(): Identity | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Identity) : null;
  } catch {
    return null;
  }
}

function store(identity: Identity): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(identity));
  } catch {
    // Private windows can block storage. The chat still works, it just asks for a key again.
  }
}

/** Reuse the saved personal key, or ask the brain for a new one. */
export async function ensureIdentity(): Promise<Identity> {
  const saved = readStored();
  if (saved) return saved;
  const userId = `demo-${crypto.randomUUID().slice(0, 8)}`;
  const res = await fetch("/api/v1/keys", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, team: "general" }),
  });
  if (!res.ok) throw new Error("Could not get a personal key.");
  const body = (await res.json()) as { key: string; default_model: string };
  const identity = { userId, team: "general", key: body.key, model: body.default_model };
  store(identity);
  return identity;
}

export function forgetIdentity(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // nothing to forget
  }
}

interface GatewayError {
  error?: { code?: string; message?: string; provider_specific_fields?: Record<string, unknown> };
}

const OUTCOMES: Outcome[] = ["allow", "mask", "warn", "local", "block"];

export async function sendChat(
  identity: Identity,
  history: ChatTurn[],
  ack?: string,
): Promise<ChatResult> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${identity.key}`,
  };
  if (ack) headers["X-DNA-Ack"] = ack;

  let res: Response;
  try {
    res = await fetch("/gateway/v1/chat/completions", {
      method: "POST",
      headers,
      body: JSON.stringify({ model: identity.model, messages: history }),
    });
  } catch {
    return {
      kind: "error",
      message: "We could not reach the server. Check your connection and try again.",
    };
  }

  if (res.ok) {
    const body = (await res.json()) as { choices?: { message?: { content?: string } }[] };
    const decision = res.headers.get("x-dna-decision") ?? "allow";
    const outcome = OUTCOMES.includes(decision as Outcome) ? (decision as Outcome) : "allow";
    const reasons = decodeURIComponent(res.headers.get("x-dna-reasons") ?? "")
      .split("; ")
      .filter(Boolean);
    return { kind: "answer", text: body.choices?.[0]?.message?.content ?? "", outcome, reasons };
  }

  let detail: GatewayError = {};
  try {
    detail = (await res.json()) as GatewayError;
  } catch {
    // keep the generic message below
  }
  const fields = detail.error?.provider_specific_fields ?? {};
  const reasons = Array.isArray(fields.reasons) ? (fields.reasons as string[]) : [];
  if (res.status === 409 && fields.type === "warn") return { kind: "warn", reasons };
  if (res.status === 403 && fields.type === "block") {
    return {
      kind: "block",
      reasons,
      alternative: String(fields.approved_alternative ?? "Use the company chat."),
    };
  }
  if (res.status === 401) {
    forgetIdentity();
    return {
      kind: "error",
      message: "Your key is no longer valid. Reload the page to get a new one.",
    };
  }
  if (res.status === 503 && typeof fields.message === "string") {
    return { kind: "error", message: `${fields.message} ${String(fields.next ?? "")}`.trim() };
  }
  return { kind: "error", message: "Something went wrong on our side. Try again in a minute." };
}
