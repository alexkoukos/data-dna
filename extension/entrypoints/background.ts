import {
  askLocal,
  checkRemote,
  postEvents,
  postRewriteUsed,
  refreshPolicy,
  safeBrainUrl,
} from "../src/api";
import { bumpStats, getPolicy, getSettings, saveSettings } from "../src/storage";
import { companyChatUrl } from "../src/handoff";
import type { Msg } from "../src/types";

/** Pages the content script runs on. A message from anywhere else is ignored. */
const AI_HOSTS = new Set([
  "chatgpt.com",
  "chat.openai.com",
  "claude.ai",
  "gemini.google.com",
  "localhost",
]);

/** Messages a web page's content script may send. The rest come from Sentry's own pages only. */
const PAGE_MESSAGES = new Set<Msg["type"]>([
  "l2",
  "policy",
  "visit",
  "event",
  "override",
  "rewriteUsed",
  "askLocal",
  "openPanel",
  "openChat",
]);

function allowedSender(sender: chrome.runtime.MessageSender, type: Msg["type"]): boolean {
  if (sender.id !== chrome.runtime.id) return false;
  // Our own pages (popup, side panel, options), also when they are open in a tab.
  if (sender.url?.startsWith(chrome.runtime.getURL("/"))) return true;
  if (!sender.tab) return true;
  if (!PAGE_MESSAGES.has(type)) return false;
  try {
    return AI_HOSTS.has(new URL(sender.url ?? sender.tab.url ?? "").hostname);
  } catch {
    return false;
  }
}

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

const AI_PAGES = [
  "https://chatgpt.com/*",
  "https://chat.openai.com/*",
  "https://claude.ai/*",
  "https://gemini.google.com/*",
  "http://localhost:3100/*",
];

/**
 * Connect without asking anything: use the default server and, in the demo, the first demo person.
 * A company's own setup (a Chrome policy or a pairing code) is never overwritten.
 */
async function autoConnect(): Promise<boolean> {
  const s = await getSettings();
  if (s.token || s.demoUser) return true;
  const base = safeBrainUrl(s.brainUrl);
  if (!base) return false;
  try {
    const res = await fetch(`${base}/v1/demo-users`);
    if (!res.ok) return false;
    const users = (await res.json()) as { user: string; team: string }[];
    const first = users[0];
    if (!first) return false;
    await saveSettings({ demoUser: first.user, userLabel: `${first.user} (${first.team})` });
    void refreshPolicy();
    return true;
  } catch {
    return false;
  }
}

/** A page that was open before the extension arrived has no content script yet: add it, no reload needed. */
async function protectOpenTabs() {
  const tabs = await chrome.tabs.query({ url: AI_PAGES });
  for (const t of tabs) {
    if (t.id === undefined) continue;
    chrome.scripting
      .executeScript({ target: { tabId: t.id }, files: ["content-scripts/ai-sites.js"] })
      .catch(() => undefined);
  }
}

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
  // The token and the policy are for Sentry's own pages and service worker, never for a page script.
  void chrome.storage.local.setAccessLevel?.({ accessLevel: "TRUSTED_CONTEXTS" });
  void chrome.storage.session.setAccessLevel?.({ accessLevel: "TRUSTED_CONTEXTS" });
  void refreshPolicy();
  void autoConnect();
  chrome.runtime.onInstalled.addListener(() => {
    void autoConnect();
    void protectOpenTabs();
    void refreshPolicy();
    void chrome.alarms.create("policy", { periodInMinutes: 1 });
    void chrome.alarms.create("flush", { periodInMinutes: 0.5 });
  });
  chrome.alarms.onAlarm.addListener((a) => {
    if (a.name === "policy") {
      void refreshPolicy();
      void autoConnect(); // keeps trying until the server is up
    }
    if (a.name === "flush") void flush();
  });

  chrome.runtime.onMessage.addListener((raw: Msg, sender, reply) => {
    const msg = raw;
    if (!msg || typeof msg.type !== "string" || !allowedSender(sender, msg.type)) {
      reply(null);
      return false;
    }
    (async () => {
      switch (msg.type) {
        case "l2":
          reply(await checkRemote(msg.text, msg.tool, msg.url, msg.attachments));
          return;
        case "policy": {
          // `force` is the popup's "Refresh now": wait for the server's answer instead of the cache.
          // A page script cannot force it, so a page cannot make the worker call the server in a loop.
          reply(
            msg.force && sender.url?.startsWith(chrome.runtime.getURL("/"))
              ? await refreshPolicy()
              : await getPolicy(),
          );
          if (!msg.force) void refreshPolicy();
          return;
        }
        case "connect":
          reply({ ok: await autoConnect() });
          return;
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
        case "rewriteUsed":
          reply({ ok: await postRewriteUsed() });
          return;
        case "askLocal":
          reply(await askLocal(msg.prompt));
          return;
        case "openPanel": {
          // Open first, in the same breath as the click (Chrome only allows it right after a user
          // action), then hand over the prompt. If the browser has no side panel, use a tab.
          const tabId = sender.tab?.id;
          const opening =
            tabId !== undefined && chrome.sidePanel?.open
              ? chrome.sidePanel.open({ tabId }).then(
                  () => true,
                  () => false,
                )
              : Promise.resolve(false);
          await chrome.storage.session.set({ pendingPrompt: msg.prompt });
          if (!(await opening))
            await chrome.tabs.create({ url: chrome.runtime.getURL("/sidepanel.html?tab=1") });
          reply({ ok: true });
          return;
        }
        case "openChat":
          // A stopped file: open Company Chat in a tab so the person can upload it there. No new
          // permission is needed to open a tab.
          await chrome.tabs.create({ url: companyChatUrl(msg.url, msg.tool, msg.file) });
          reply({ ok: true });
          return;
        default:
          reply(null);
      }
    })();
    return true;
  });
});
