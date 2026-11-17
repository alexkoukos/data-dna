import { askLocal, checkRemote, postEvents, refreshPolicy } from "../src/api";
import { bumpStats, getPolicy } from "../src/storage";
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
          reply(await checkRemote(msg.text, msg.tool, msg.url));
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
          await chrome.storage.session.set({ pendingPrompt: msg.prompt });
          if (sender.tab?.id !== undefined) await chrome.sidePanel.open({ tabId: sender.tab.id });
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
