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
  | { kind: "warn"; reasons: string[]; suggestion?: string }
  | { kind: "block"; reasons: string[]; alternative: string }
  | { kind: "error"; message: string };

const STORAGE_KEY = "dna.identity";

export function savedIdentity(): Identity | null {
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
  const saved = savedIdentity();
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

const OUTCOMES: Outcome[] = ["allow", "mask", "warn", "local", "block", "rerouted"];

const CHECK_FAILED = "The answer could not be checked, so it was not shown. Try again in a minute.";

/**
 * Read a streamed answer (server-sent events) and report the text so far after every piece.
 * The gateway sends only text it has already checked; an error event mid-way withholds the rest.
 */
async function readStream(
  body: ReadableStream<Uint8Array>,
  onText: (soFar: string) => void,
): Promise<{ text: string } | { error: string }> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let text = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: true });
    if (done) buffer += decoder.decode();
    const events = buffer.split(/\r?\n\r?\n/);
    buffer = done ? "" : (events.pop() ?? "");
    for (const event of events) {
      const data = event
        .split(/\r?\n/)
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim())
        .join("\n");
      if (!data || data === "[DONE]") continue;
      let chunk: { choices?: { delta?: { content?: string | null } }[]; error?: unknown };
      try {
        chunk = JSON.parse(data) as typeof chunk;
      } catch {
        continue;
      }
      if (chunk.error) {
        void reader.cancel().catch(() => undefined);
        return { error: CHECK_FAILED };
      }
      const piece = chunk.choices?.[0]?.delta?.content;
      if (piece) {
        text += piece;
        onText(text);
      }
    }
    if (done) return { text };
  }
}

export async function sendChat(
  identity: Identity,
  history: ChatTurn[],
  ack?: string,
  reroute = false,
  onText?: (soFar: string) => void,
): Promise<ChatResult> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${identity.key}`,
  };
  if (ack) headers["X-DNA-Ack"] = ack;
  // X31: "send it to Company AI instead". The gate masks the text and answers on the company model.
  if (reroute) headers["X-DNA-Reroute"] = "1";

  let res: Response;
  try {
    res = await fetch("/gateway/v1/chat/completions", {
      method: "POST",
      headers,
      // With a listener the answer streams: the company's own model sends text as it writes it.
      body: JSON.stringify({
        model: identity.model,
        messages: history,
        ...(onText ? { stream: true } : {}),
      }),
    });
  } catch {
    return {
      kind: "error",
      message: "We could not reach the server. Check your connection and try again.",
    };
  }

  if (res.ok) {
    const decision = res.headers.get("x-dna-decision") ?? "allow";
    const outcome = OUTCOMES.includes(decision as Outcome) ? (decision as Outcome) : "allow";
    const reasons = decodeURIComponent(res.headers.get("x-dna-reasons") ?? "")
      .split("; ")
      .filter(Boolean);
    const streamed = (res.headers.get("content-type") ?? "").includes("text/event-stream");
    if (streamed && res.body && onText) {
      let read: { text: string } | { error: string };
      try {
        read = await readStream(res.body, onText);
      } catch {
        return {
          kind: "error",
          message: "The connection dropped before the answer finished. Try again.",
        };
      }
      if ("error" in read) return { kind: "error", message: read.error };
      return { kind: "answer", text: read.text, outcome, reasons };
    }
    const body = (await res.json()) as { choices?: { message?: { content?: string } }[] };
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
  if (res.status === 409 && fields.type === "warn") {
    const suggestion =
      typeof fields.suggested_rewrite === "string" && fields.suggested_rewrite
        ? fields.suggested_rewrite
        : undefined;
    return { kind: "warn", reasons, suggestion };
  }
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

/** X19: tell the brain the person took the safe rewrite. Only a count is kept. Never throws. */
export async function countCoachingAccepted(): Promise<void> {
  try {
    await fetch("/api/v1/coaching/accepted", { method: "POST" });
  } catch {
    // counting is best effort; the message itself must not fail because of it
  }
}
