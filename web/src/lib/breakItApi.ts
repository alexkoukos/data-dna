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
}

export interface TryExample {
  category: string;
  text: string;
}

/** Runs the whole pipeline on a text. Nothing is stored on the server. */
export async function tryText(text: string): Promise<TryResult> {
  const res = await fetch("/api/v1/try", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
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
