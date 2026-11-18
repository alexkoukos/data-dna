export interface Digest {
  team: string;
  note: string;
  start: string | null;
  end: string | null;
  incidents: number;
  previous: number;
  change: number;
  change_pct: number | null;
  outcomes: Record<string, number>;
  categories: { category: string; count: number }[];
  tools: { name: string; approval: string; count: number }[];
  tips: string[];
  markdown: string;
  email: { subject: string; body: string };
}

export async function fetchDigestTeams(): Promise<string[]> {
  const res = await fetch("/api/v1/digest/teams");
  if (!res.ok) throw new Error("The teams could not be loaded.");
  return (await res.json()) as string[];
}

export async function fetchDigest(team: string): Promise<Digest> {
  const res = await fetch(`/api/v1/digest?team=${encodeURIComponent(team)}`);
  if (!res.ok) throw new Error("The digest could not be loaded.");
  return (await res.json()) as Digest;
}

export const markdownUrl = (team: string) => `/api/v1/digest.md?team=${encodeURIComponent(team)}`;

export function trendText(d: Pick<Digest, "incidents" | "previous" | "change" | "change_pct">) {
  if (d.previous === 0) return `${d.incidents} this week, none the week before.`;
  if (d.change === 0) return `${d.incidents} this week, unchanged on last week (${d.previous}).`;
  const word = d.change > 0 ? "up" : "down";
  const pct = d.change_pct === null ? "" : ` (${Math.abs(d.change_pct)}%)`;
  return `${d.incidents} this week, ${word} by ${Math.abs(d.change)}${pct} on last week (${d.previous}).`;
}
