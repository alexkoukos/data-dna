import raw from "../../../shared/rules.json";

/** Rules come from shared/rules.json. `{W}` is a Unicode word character, `(?P<v>` becomes `(?<v>`. */
export function compile(source: string, flags = ""): RegExp {
  const expanded = source.replaceAll("{W}", "\\p{L}\\p{N}_").replaceAll("(?P<", "(?<");
  return new RegExp(expanded, `gu${flags}`);
}

export interface PatternRule {
  entity: string;
  category: string;
  rx: RegExp;
}

export interface DigitCheck {
  min: number;
  max: number;
  validator: "afm" | "amka" | "luhn";
  entity: string;
  category: string;
}

export const IBAN = {
  entity: raw.iban.entity,
  category: raw.iban.category,
  rx: compile(raw.iban.regex),
  lengths: raw.iban.lengths as Record<string, number>,
};

export const DIGITS = {
  rx: compile(raw.digits.regex),
  checks: raw.digits.checks.map((c): DigitCheck => ({
    min: c.length[0] ?? 0,
    max: c.length[1] ?? 0,
    validator: c.validator as DigitCheck["validator"],
    entity: c.entity,
    category: c.category,
  })),
};

export const SECRETS: PatternRule[] = raw.secrets.map((s) => ({
  entity: s.entity,
  category: s.category,
  rx: compile(s.regex),
}));

export const PATTERNS: PatternRule[] = raw.patterns.map((p) => ({
  entity: p.entity,
  category: p.category,
  rx: compile(p.regex, "flags" in p ? String(p.flags) : ""),
}));

export const NORMALISE = {
  invisible: compile(raw.normalise.invisible),
  spacedDigits: compile(raw.normalise.spacedDigits),
  base64: compile(raw.normalise.base64),
  hex: compile(raw.normalise.hex),
};

export const SOURCE_CODE = {
  minHits: raw.sourceCode.minHits,
  hints: raw.sourceCode.hints.map((h) => new RegExp(h, "m")),
};
