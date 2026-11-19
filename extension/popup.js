import { getConfig, getCounts } from "./shared.js";

const $ = (id) => document.getElementById(id);

async function init() {
  const counts = await getCounts();
  for (const k of ["masked", "warned", "blocked"])
    $(k).textContent = String(counts[k]);
  const { key } = await getConfig();
  const status = $("status");
  if (!key) {
    status.className = "bad";
    status.textContent = "Add your personal key in Settings.";
    return;
  }
  const out = await chrome.runtime.sendMessage({ type: "me" });
  if (out.ok) {
    status.className = "ok";
    status.textContent = `Signed in as ${out.body.user_id}.${out.body.shadow_mode ? " Shadow mode: recording only." : ""}`;
    $("incidents").href = globalThis.SentryLogic.safeHref(out.body.incidents_url);
  } else {
    status.className = "bad";
    status.textContent =
      out.status === 401
        ? "The gate does not accept this key."
        : "Sentry offline. Nothing is blocked while it is.";
    $("incidents").hidden = true;
  }
}
init();
