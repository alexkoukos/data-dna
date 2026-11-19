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
  let url;
  try {
    url = new URL(brainUrl);
  } catch {
    $("result").textContent = "Not saved: that address is not a valid URL.";
    return;
  }
  const origin = url.origin + "/*";
  const local = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(url.origin);
  if (!local && url.protocol !== "https:") {
    $("result").textContent =
      "Not saved: use https for a remote gate (http is only for this computer).";
    return;
  }
  if (!local && !(await chrome.permissions.request({ origins: [origin] }))) {
    $("result").textContent =
      "Not saved: the browser needs your permission to reach that address.";
    return;
  }
  await chrome.storage.local.set({ key, brainUrl });
  $("result").textContent = "Saved.";
});
