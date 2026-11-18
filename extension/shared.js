// Small helpers shared by the background worker, popup and options page.
// The extension stores only: the key, the brain URL and a daily counter for the popup.
export const DEFAULT_BRAIN = "http://localhost:8001";

export async function getConfig() {
  const { key = "", brainUrl = DEFAULT_BRAIN } = await chrome.storage.local.get(
    ["key", "brainUrl"],
  );
  return { key, brainUrl: (brainUrl || DEFAULT_BRAIN).replace(/\/+$/, "") };
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export async function getCounts() {
  const { counts } = await chrome.storage.local.get("counts");
  if (!counts || counts.day !== today())
    return { day: today(), masked: 0, warned: 0, blocked: 0 };
  return counts;
}

export async function bump(decision) {
  const field = {
    mask: "masked",
    warn: "warned",
    block: "blocked",
    local: "blocked",
  }[decision];
  if (!field) return;
  const counts = await getCounts();
  counts[field] += 1;
  await chrome.storage.local.set({ counts });
}
