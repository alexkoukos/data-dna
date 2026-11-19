import { NORMALISE } from "./rules";

export interface Normalised {
  text: string;
  /** Other readings of the same text (decoded or de-spaced). Findings here cannot be masked in place. */
  views: string[];
  signals: string[];
}

// First code point of the digit block of common scripts, zero to nine.
const DIGIT_ZEROS = [0x0660, 0x06f0, 0x0966, 0x09e6, 0x0e50, 0xff10];

function asciiDigits(text: string): string {
  return text.replace(/\p{Nd}/gu, (ch) => {
    const cp = ch.codePointAt(0) ?? 0;
    const zero = DIGIT_ZEROS.find((z) => cp >= z && cp <= z + 9);
    return zero === undefined ? ch : String(cp - zero);
  });
}

function tryBase64(token: string): string | null {
  try {
    const padded = token + "=".repeat((4 - (token.length % 4)) % 4);
    const bytes = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
    const out = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    const printable =
      [...out].filter((c) => /[\P{C}\n\t]/u.test(c)).length / Math.max(out.length, 1);
    return printable > 0.9 && out.length >= 6 ? out : null;
  } catch {
    return null;
  }
}

function tryHex(chunk: string): string | null {
  const bytes = chunk.match(/../g)?.map((h) => parseInt(h, 16)) ?? [];
  if (bytes.some((b) => b < 32 || b > 126)) return null;
  const out = String.fromCharCode(...bytes);
  return out.length >= 6 ? out : null;
}

export function normalise(raw: string): Normalised {
  const signals = new Set<string>();
  let text = raw.normalize("NFKC");
  const stripped = text.replace(NORMALISE.invisible, "");
  if (stripped !== text) {
    signals.add("invisible_characters");
    text = stripped;
  }
  const digits = asciiDigits(text);
  if (digits !== text) {
    signals.add("unicode_digits");
    text = digits;
  }

  const views: string[] = [];
  for (const m of text.matchAll(NORMALISE.spacedDigits)) {
    const chunk = m[0];
    if (/[ .\-/\t\r\n]/.test(chunk)) {
      views.push(chunk.replace(/[ .\-/\t\r\n]/g, ""));
      signals.add("spaced_digits");
    }
  }
  for (const m of text.matchAll(NORMALISE.hex)) {
    const decoded = tryHex(m[0]);
    if (decoded) {
      views.push(decoded);
      signals.add("hex");
    }
  }
  for (const m of text.matchAll(NORMALISE.base64)) {
    const decoded = tryBase64(m[0]);
    if (decoded) {
      views.push(decoded);
      signals.add("base64");
    }
  }
  return { text, views, signals: [...signals].sort() };
}
