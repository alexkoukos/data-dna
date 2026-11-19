import { afmOk, amkaOk, ibanOk, luhnOk } from "./validators";
import { DIGITS, IBAN, PATTERNS, SECRETS, SOURCE_CODE } from "./rules";
import { normalise } from "./normalize";

export interface Finding {
  entity: string;
  category: string;
  start: number;
  end: number;
  value: string;
  /** Found in a decoded or de-spaced view, so it cannot be replaced in the composer. */
  hidden?: boolean;
}

const VALIDATORS = {
  afm: afmOk,
  amka: amkaOk,
  luhn: luhnOk,
} as const;

export function findPatterns(text: string): Finding[] {
  const loose: Finding[] = [];
  const found: Finding[] = [];
  for (const rule of PATTERNS) {
    for (const m of text.matchAll(rule.rx)) {
      const value = m.groups?.v ?? m[0];
      const start = (m.index ?? 0) + m[0].indexOf(value);
      loose.push({
        entity: rule.entity,
        category: rule.category,
        start,
        end: start + value.length,
        value,
      });
    }
  }
  for (const m of text.matchAll(IBAN.rx)) {
    if (ibanOk(m[0], IBAN.lengths)) {
      const start = m.index ?? 0;
      found.push({
        entity: IBAN.entity,
        category: IBAN.category,
        start,
        end: start + m[0].length,
        value: m[0],
      });
    }
  }
  for (const m of text.matchAll(DIGITS.rx)) {
    const d = m[0];
    const check = DIGITS.checks.find((c) => d.length >= c.min && d.length <= c.max);
    if (check && VALIDATORS[check.validator](d)) {
      const start = m.index ?? 0;
      found.push({
        entity: check.entity,
        category: check.category,
        start,
        end: start + d.length,
        value: d,
      });
    }
  }
  for (const rule of SECRETS) {
    for (const m of text.matchAll(rule.rx)) {
      const start = m.index ?? 0;
      found.push({
        entity: rule.entity,
        category: rule.category,
        start,
        end: start + m[0].length,
        value: m[0],
      });
    }
  }
  // Checksum-validated findings and secrets win; looser shapes (emails, plates) never split them.
  return dedupe(addWithoutOverlap(dedupe(found), dedupe(loose)));
}

function addWithoutOverlap(base: Finding[], extra: Finding[]): Finding[] {
  const out = [...base];
  for (const f of extra) {
    if (!out.some((b) => f.start < b.end && b.start < f.end)) out.push(f);
  }
  return out;
}

/** Checksum-validated and longer findings win over overlapping ones. */
function dedupe(items: Finding[]): Finding[] {
  const sorted = [...items].sort(
    (a, b) => a.start - b.start || b.end - b.start - (a.end - a.start),
  );
  const out: Finding[] = [];
  for (const f of sorted) {
    const last = out[out.length - 1];
    if (last && f.start < last.end) continue;
    out.push(f);
  }
  return out;
}

const clientRx = new WeakMap<string[], RegExp | null>();

/** Client names from the company's list. Names of 4+ letters match in any case; short aliases (HML) only as written. */
export function findClients(text: string, clients: string[]): Finding[] {
  if (!clients.length) return [];
  let rx = clientRx.get(clients);
  if (rx === undefined) {
    const esc = (n: string) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const long = clients.filter((n) => n.length >= 4).map(esc);
    const short = clients.filter((n) => n.length === 3).map(esc);
    const W = "[\\p{L}\\p{N}_]";
    const parts = [
      long.length ? `(?<!${W})(?:${long.join("|")})(?!${W})` : "",
      short.length ? `(?<!${W})(?:${short.join("|")})(?!${W})` : "",
    ].filter(Boolean);
    rx = parts.length ? new RegExp(parts.join("|"), "giu") : null;
    clientRx.set(clients, rx);
  }
  if (!rx) return [];
  const out: Finding[] = [];
  for (const m of text.matchAll(rx)) {
    const value = m[0];
    // A three-letter alias must be written exactly as in the list (so "tec" the word is not a client).
    if (value.length === 3 && !clients.includes(value)) continue;
    const start = m.index ?? 0;
    out.push({
      entity: "CLIENT",
      category: "client_name",
      start,
      end: start + value.length,
      value,
    });
  }
  return out;
}

export function looksLikeSourceCode(text: string): boolean {
  if (text.length < 40) return false;
  const hits = SOURCE_CODE.hints.filter((h) => h.test(text)).length;
  return hits >= SOURCE_CODE.minHits;
}

export interface Scan {
  /** The text after clean-up (invisible characters removed, digits from other scripts converted). */
  text: string;
  findings: Finding[];
  signals: string[];
  sourceCode: boolean;
}

export function scan(raw: string, clients: string[] = []): Scan {
  const norm = normalise(raw);
  const direct = addWithoutOverlap(findPatterns(norm.text), findClients(norm.text, clients));
  const hidden: Finding[] = [];
  for (const view of norm.views) {
    for (const f of findPatterns(view)) hidden.push({ ...f, hidden: true });
  }
  const seen = new Set(direct.map((f) => `${f.entity}:${f.value.replaceAll(" ", "")}`));
  const extra = hidden.filter((f) => !seen.has(`${f.entity}:${f.value.replaceAll(" ", "")}`));
  return {
    text: norm.text,
    findings: [...direct, ...extra],
    signals: norm.signals,
    sourceCode: looksLikeSourceCode(norm.text),
  };
}

export interface MaskResult {
  text: string;
  /** placeholder to real value. Kept only in memory in the tab. */
  placeholders: Record<string, string>;
}

export function mask(text: string, findings: Finding[]): MaskResult {
  const placeholders: Record<string, string> = {};
  const counters: Record<string, number> = {};
  const parts: string[] = [];
  let last = 0;
  for (const f of [...findings].filter((x) => !x.hidden).sort((a, b) => a.start - b.start)) {
    counters[f.entity] = (counters[f.entity] ?? 0) + 1;
    const token = `[${f.entity}_${counters[f.entity]}]`;
    placeholders[token] = f.value;
    parts.push(text.slice(last, f.start), token);
    last = f.end;
  }
  parts.push(text.slice(last));
  return { text: parts.join(""), placeholders };
}

export function unmask(text: string, placeholders: Record<string, string>): string {
  let out = text;
  for (const [token, value] of Object.entries(placeholders)) out = out.replaceAll(token, value);
  return out;
}
