import type { Outcome } from "../components/OutcomeChip";

export interface StoredTurn {
  id: number;
  from: "user" | "assistant";
  text: string;
  outcome?: Outcome;
  reasons?: string[];
  failed?: boolean;
}

export interface Chat {
  id: string;
  title: string;
  updated: number;
  turns: StoredTurn[];
}

const KEY = "sentry.chats";
const MAX_CHATS = 50;

/** Chats live in this browser only (the company AI keeps no history of its own). */
export function loadChats(): Chat[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed)
      ? (parsed as Chat[]).filter((c) => typeof c?.id === "string" && Array.isArray(c.turns))
      : [];
  } catch {
    return [];
  }
}

export function saveChats(chats: Chat[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(chats.slice(0, MAX_CHATS)));
  } catch {
    // Private windows can block storage; the chat still works for this visit.
  }
}

export const newChat = (): Chat => ({
  id: crypto.randomUUID(),
  title: "New chat",
  updated: Date.now(),
  turns: [],
});

/** The first question, trimmed to a sidebar-friendly title. */
export function titleFrom(text: string): string {
  const t = text.replace(/\s+/g, " ").trim();
  return t.length > 42 ? `${t.slice(0, 41).trimEnd()}…` : t || "New chat";
}

const DAY = 86_400_000;
const startOfDay = (t: number) => {
  const d = new Date(t);
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
};

/** Today, Yesterday, Previous 7 days, Older. Newest first inside each group; empty groups are left out. */
export function groupByPeriod(
  chats: Chat[],
  now = Date.now(),
): { period: string; chats: Chat[] }[] {
  const today = startOfDay(now);
  const buckets: Record<string, Chat[]> = {
    Today: [],
    Yesterday: [],
    "Previous 7 days": [],
    Older: [],
  };
  for (const c of [...chats].sort((a, b) => b.updated - a.updated)) {
    const age = today - startOfDay(c.updated);
    const key =
      age <= 0 ? "Today" : age <= DAY ? "Yesterday" : age <= 7 * DAY ? "Previous 7 days" : "Older";
    buckets[key]?.push(c);
  }
  return Object.entries(buckets)
    .filter(([, list]) => list.length)
    .map(([period, list]) => ({ period, chats: list }));
}
