import { askLocal, checkRemote, createHandoff, postEvents, refreshPolicy } from "../src/api";
import { bumpStats, getPolicy, getSettings } from "../src/storage";
import type { Msg } from "../src/types";

interface QueuedEvent {
  ts: number;
  tool: string;
  host: string;
  offline?: boolean;
  kind: "visit" | "decision" | "override";
  action?: string;
  category?: string;
  reason?: string;
}

const QUEUE_CAP = 500;

async function enqueue(e: QueuedEvent) {
  const { queue } = await chrome.storage.local.get("queue");
  const list = ([...((queue as QueuedEvent[]) ?? []), e] as QueuedEvent[]).slice(-QUEUE_CAP);
  await chrome.storage.local.set({ queue: list });
  if (list.length >= 10) void flush();
}

async function flush() {
  const { queue } = await chrome.storage.local.get("queue");
  const list = (queue as QueuedEvent[]) ?? [];
  if (!list.length) return;
  if (await postEvents(list)) {
    // Events added while we were sending stay in the queue.
    const { queue: now } = await chrome.storage.local.get("queue");
    await chrome.storage.local.set({ queue: ((now as QueuedEvent[]) ?? []).slice(list.length) });
  }
}

export default defineBackground(() => {
  // A service worker can be stopped and started at any time, so the timers are re-checked on every start.
  void chrome.alarms.get("policy").then((a) => {
    if (!a) void chrome.alarms.create("policy", { periodInMinutes: 1 });
  });
  void chrome.alarms.get("flush").then((a) => {
    if (!a) void chrome.alarms.create("flush", { periodInMinutes: 0.5 });
  });
  void refreshPolicy();
  chrome.runtime.onInstalled.addListener(() => {
    void refreshPolicy();
    void chrome.alarms.create("policy", { periodInMinutes: 1 });
    void chrome.alarms.create("flush", { periodInMinutes: 0.5 });
  });
  chrome.alarms.onAlarm.addListener((a) => {
    if (a.name === "policy") void refreshPolicy();
    if (a.name === "flush") void flush();
  });

  chrome.runtime.onMessage.addListener((raw: Msg, sender, reply) => {
    const msg = raw;
    (async () => {
      switch (msg.type) {
        case "l2":
          reply(await checkRemote(msg.text, msg.tool, msg.url, msg.attachments));
          return;
        case "policy": {
          // `force` is the popup's "Refresh now": wait for the server's answer instead of the cache.
          reply(msg.force ? await refreshPolicy() : await getPolicy());
          if (!msg.force) void refreshPolicy();
          return;
        }
        case "visit":
          await enqueue({ ts: Date.now(), tool: msg.tool, host: msg.host, kind: "visit" });
          reply({ ok: true });
          return;
        case "event":
          await enqueue({
            ts: Date.now(),
            tool: msg.tool,
            host: msg.host,
            kind: "decision",
            action: msg.action,
            category: msg.category,
            offline: msg.offline,
          });
          await bumpStats(msg.action, msg.tool, msg.category ?? "");
          reply({ ok: true });
          return;
        case "override":
          await enqueue({
            ts: Date.now(),
            tool: msg.tool,
            host: msg.host,
            kind: "override",
            reason: msg.reason,
          });
          reply({ ok: true });
          return;
        case "askLocal":
          reply(await askLocal(msg.prompt));
          return;
        case "openPanel": {
          // The company chat reads files too, and a tab works in every browser (Brave has no side
          // panel). The text or file is passed on through the company server, once.
          const id =
            msg.prompt || msg.attachments?.length
              ? await createHandoff(msg.prompt, msg.attachments ?? [])
              : null;
          const base = await companyChatUrl();
          await chrome.tabs.create({
            url: id ? `${base}?handoff=${encodeURIComponent(id)}` : base,
          });
          reply({ ok: true });
          return;
        }
        default:
          reply(null);
      }
    })();
    return true;
  });
});

/** The company chat page on the dashboard, next to the brain (port 8001 -> dashboard 3000). */
async function companyChatUrl(): Promise<string> {
  const { brainUrl } = await getSettings();
  try {
    const u = new URL(brainUrl);
    if (u.port === "8001") u.port = "3000";
    return `${u.origin}/chat`;
  } catch {
    return "http://localhost:3000/chat";
  }
}
