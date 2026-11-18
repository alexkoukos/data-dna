import { DEFAULT_BRAIN, getConfig } from "./shared.js";

const $ = (id) => document.getElementById(id);
$("ext-id").textContent = chrome.runtime.id;

(async () => {
  const { key, brainUrl } = await getConfig();
  $("key").value = key;
  $("brain").value = brainUrl;
})();

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const key = $("key").value.trim();
  const brainUrl = ($("brain").value.trim() || DEFAULT_BRAIN).replace(
    /\/+$/,
    "",
  );
  const origin = new URL(brainUrl).origin + "/*";
  const local = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(
    new URL(brainUrl).origin,
  );
  if (!local && !(await chrome.permissions.request({ origins: [origin] }))) {
    $("result").textContent =
      "Not saved: the browser needs your permission to reach that address.";
    return;
  }
  await chrome.storage.local.set({ key, brainUrl });
  $("result").textContent = "Saved.";
});
