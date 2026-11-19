/** Local policy decision, same precedence as services/brain/src/brain/policy/engine.py. */
export type Action = "allow" | "mask" | "warn" | "local" | "block";

export const PRECEDENCE: Record<Action, number> = {
  allow: 0,
  mask: 1,
  warn: 2,
  local: 3,
  block: 4,
};

export type FailMode = "fail_open" | "fail_closed";

export interface Policy {
  version: number;
  categories: Record<string, Action>;
  sensitivity: Record<string, Action>;
  failMode: Record<string, FailMode>;
  /** Client names and aliases from the company's client list. */
  clients: string[];
  tools: Record<
    string,
    { approval: "approved" | "tolerated" | "unapproved"; alternative?: string }
  >;
}

export const DEFAULT_POLICY: Policy = {
  version: 0,
  categories: {
    greek_id: "mask",
    iban: "mask",
    card: "mask",
    secret: "mask",
    person_email_phone: "mask",
    client_name: "warn",
    source_code: "warn",
    injection: "block",
    honeytoken: "block",
  },
  sensitivity: { internal: "local", confidential: "local", restricted: "block" },
  failMode: { restricted: "fail_closed", other: "fail_open" },
  clients: [],
  tools: {},
};

export interface Decision {
  action: Action;
  reasons: string[];
}

export function worst(a: Action, b: Action): Action {
  return PRECEDENCE[b] > PRECEDENCE[a] ? b : a;
}

export function decideLocal(
  categories: string[],
  policy: Policy,
  opts: { hiddenFinding?: boolean } = {},
): Decision {
  let action: Action = "allow";
  const reasons: string[] = [];
  for (const category of new Set(categories)) {
    const chosen = policy.categories[category] ?? "warn";
    action = worst(action, chosen);
  }
  if (opts.hiddenFinding && action === "mask") {
    // Evasion that hides a value cannot be masked in place, so ask the person first.
    action = "warn";
  }
  return { action, reasons };
}
