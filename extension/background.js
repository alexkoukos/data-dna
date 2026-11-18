// The only code that talks to the network, and only to the brain URL the person configured.
// The page's content script asks us, so the call carries the extension's origin (the one CORS allows).
import { bump, getConfig } from "./shared.js";

async function call(path, init) {
  const { key, brainUrl } = await getConfig();
  if (!key) return { ok: false, status: 0, error: "no-key" };
  try {
    const res = await fetch(brainUrl + path, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${key}`,
      },
      signal: AbortSignal.timeout(8000),
    });
    const body = await res.json().catch(() => ({}));
    return res.ok
      ? { ok: true, status: res.status, body }
      : { ok: false, status: res.status, error: "refused" };
  } catch {
    return { ok: false, status: 0, error: "offline" };
  }
}

async function handle(msg) {
  if (msg.type === "inspect") {
    const out = await call("/v1/extension/inspect", {
      method: "POST",
      body: JSON.stringify({ text: msg.text, model: "ChatGPT (personal)" }),
    });
    // Count only what was acted on. Shadow mode changes nothing, so it counts nothing.
    if (out.ok && !out.body.shadow) await bump(out.body.decision);
    return out;
  }
  if (msg.type === "ack") {
    return call("/v1/extension/ack", {
      method: "POST",
      body: JSON.stringify({ reason: msg.reason || "" }),
    });
  }
  if (msg.type === "me") return call("/v1/extension/me", { method: "GET" });
  return { ok: false, error: "unknown" };
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  handle(msg).then(reply);
  return true;
});
