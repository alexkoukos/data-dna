import copy from "./mascot.copy.json";

export type MascotState = keyof typeof copy;
export type Lang = "en" | "el";

/** Fixed speech lines (never generated). Max 80 characters each, checked by a test. */
export function line(state: MascotState, lang: Lang = currentLang()): string {
  return copy[state][lang];
}

export function currentLang(): Lang {
  try {
    const saved = localStorage.getItem("pyli.lang");
    if (saved === "el" || saved === "en") return saved;
  } catch {
    // Fall through to the browser language.
  }
  return typeof navigator !== "undefined" && navigator.language?.startsWith("el") ? "el" : "en";
}

export const STATES = Object.keys(copy) as MascotState[];
