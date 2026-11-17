import { DEFAULT_POLICY, type Policy } from "./detect/policy";
import { DEFAULT_SETTINGS, type Settings } from "./types";

/**
 * Settings set by IT with a Chrome policy. On a browser with no policy, managed storage can hang
 * instead of answering, so it only gets a moment, and the answer is remembered for a while.
 */
let managedCache: { at: number; value: Partial<Settings> } | null = null;

async function readManaged(): Promise<Partial<Settings>> {
  if (managedCache && Date.now() - managedCache.at < 60_000) return managedCache.value;
  const value = await Promise.race([
    chrome.storage.managed.get(null).catch(() => ({})),
    new Promise<Record<string, never>>((resolve) => setTimeout(() => resolve({}), 150)),
  ]);
  managedCache = { at: Date.now(), value: value as Partial<Settings> };
  return managedCache.value;
}

export async function getSettings(): Promise<Settings> {
  const [local, managed] = await Promise.all([chrome.storage.local.get("settings"), readManaged()]);
  return {
    ...DEFAULT_SETTINGS,
    ...managed,
    ...(local.settings as Partial<Settings>),
  };
}

export async function saveSettings(patch: Partial<Settings>): Promise<Settings> {
  const next = { ...(await getSettings()), ...patch };
  await chrome.storage.local.set({ settings: next });
  return next;
}

export async function getPolicy(): Promise<Policy & { etag?: string }> {
  const { policy } = await chrome.storage.local.get("policy");
  return (policy as Policy & { etag?: string }) ?? DEFAULT_POLICY;
}

export async function savePolicy(policy: Policy & { etag?: string }) {
  await chrome.storage.local.set({ policy });
}

export interface DayStats {
  day: string;
  checked: number;
  masked: number;
  warned: number;
  blocked: number;
  local: number;
}

export interface RecentEvent {
  ts: number;
  tool: string;
  action: string;
  reason: string;
}

const today = () => new Date().toISOString().slice(0, 10);

export async function bumpStats(action: string, tool: string, reason: string) {
  const { stats, recent } = await chrome.storage.local.get(["stats", "recent"]);
  const s: DayStats =
    (stats as DayStats | undefined)?.day === today()
      ? (stats as DayStats)
      : { day: today(), checked: 0, masked: 0, warned: 0, blocked: 0, local: 0 };
  s.checked += 1;
  if (action === "mask") s.masked += 1;
  if (action === "warn") s.warned += 1;
  if (action === "block") s.blocked += 1;
  if (action === "local") s.local += 1;
  const list = (
    [
      { ts: Date.now(), tool, action, reason },
      ...((recent as RecentEvent[]) ?? []),
    ] as RecentEvent[]
  ).slice(0, 5);
  await chrome.storage.local.set({ stats: s, recent: list });
}
