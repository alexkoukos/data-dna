import type { Decision } from "./securityApi";

export interface Layer {
  id: string;
  level: number;
  label: string;
  fired: boolean;
  detail: string;
}

export interface TryResult {
  decision: Decision;
  reasons: string[];
  masked_text: string;
  evasion_signals: string[];
  layers: Layer[];
  caught_by: string | null;
  attempt_id: string;
}

export interface TryExample {
  category: string;
  text: string;
}

/** Runs the whole pipeline on a text. Nothing is stored on the server. */
export async function tryText(text: string, kind = "other", nickname = ""): Promise<TryResult> {
  const res = await fetch("/api/v1/try", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, kind, nickname: nickname.trim() || null }),
  });
  if (!res.ok) throw new Error("We could not check that text. Try again in a moment.");
  return (await res.json()) as TryResult;
}

export async function fetchExamples(): Promise<TryExample[]> {
  const res = await fetch("/api/v1/try/examples");
  if (!res.ok) return [];
  return (await res.json()) as TryExample[];
}

const KINDS: Record<string, string> = {
  spacing: "Spaced out",
  encoding: "Encoded",
  look_alike: "Look-alike letters",
  other_digits: "Foreign digits",
  greeklish: "Greeklish name",
  injection: "Prompt injection",
  secrets: "Hidden key",
  documents: "Rewritten document",
  honeytoken: "Decoy key",
};
export const kindLabel = (category: string) =>
  KINDS[category] ?? category.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export interface Miss {
  id: string;
  kind: string;
  preview: string;
  nickname: string | null;
  at: string;
}
export interface Breaker {
  nickname: string;
  submitted: number;
  approved: number;
}
export interface Board {
  attempts: number;
  stopped: number;
  got_through: number;
  catch_rate: number | null;
  misses: Miss[];
  top_breakers: Breaker[];
}
export interface Candidate {
  id: number;
  created_at: string;
  nickname: string | null;
  kind: string;
  expected_decision: "mask" | "warn" | "block";
  got_decision: string;
  text: string | null;
  preview: string;
}

/** The kinds a person can pick for a miss. Same list the brain accepts. */
export const KIND_IDS = [
  "spacing",
  "encoding",
  "look_alike",
  "other_digits",
  "greeklish",
  "injection",
  "secrets",
  "documents",
  "honeytoken",
  "other",
] as const;

async function problem(res: Response, fallback: string): Promise<Error> {
  const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
  return new Error(typeof body.detail === "string" ? body.detail : fallback);
}

export async function fetchBoard(): Promise<Board> {
  const res = await fetch("/api/v1/breakit/board");
  if (!res.ok) throw new Error("The leaderboard could not be loaded.");
  return (await res.json()) as Board;
}

/** "It got through": sends the raw text because the person chose to submit it as a test case. */
export async function submitMiss(body: {
  text: string;
  expected_decision: string;
  kind: string;
  nickname: string;
}): Promise<void> {
  const res = await fetch("/api/v1/breakit/candidates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, nickname: body.nickname.trim() || null }),
  });
  if (!res.ok) throw await problem(res, "We could not send that. Try again in a moment.");
}

export async function fetchQueue(): Promise<Candidate[]> {
  const res = await fetch("/api/v1/breakit/candidates");
  if (!res.ok) throw new Error("The review queue could not be loaded.");
  return (await res.json()) as Candidate[];
}

export async function review(id: number, verb: "approve" | "reject", reviewer: string) {
  const res = await fetch(`/api/v1/breakit/candidates/${id}/${verb}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer }),
  });
  if (!res.ok) throw await problem(res, "That could not be saved. Nothing was changed.");
}
