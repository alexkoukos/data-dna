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
  chrome.runtime.onInstalled.addListener(() => {
    void refreshPolicy();
    void chrome.alarms.create("policy", { periodInMinutes: 5 });
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
          const p = await getPolicy();
          void refreshPolicy();
          reply(p);
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
