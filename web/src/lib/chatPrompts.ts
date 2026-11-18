export interface PromptGroup {
  label: string;
  /** The words highlighted inside each suggestion. */
  highlight: string;
  items: string[];
}

/** Starter questions on an empty chat, grouped like the prompt-kit "suggestions" example. */
export const PROMPT_GROUPS: PromptGroup[] = [
  {
    label: "Summarise",
    highlight: "Summarise",
    items: [
      "Summarise our data retention policy in two sentences",
      "Summarise this meeting note into three action points",
      "Summarise the key risks in this contract clause",
    ],
  },
  {
    label: "Draft",
    highlight: "Draft",
    items: [
      "Draft a polite reply declining a vendor's offer",
      "Draft an email asking a customer to confirm their details",
      "Draft a short incident report from these notes",
    ],
  },
  {
    label: "Explain",
    highlight: "Explain",
    items: [
      "Explain what a masked value means in plain words",
      "Explain the difference between GDPR and our internal policy",
      "Explain how to report a data leak",
    ],
  },
  {
    label: "Review",
    highlight: "Review",
    items: [
      "Review this paragraph for personal data before I send it",
      "Review this email for a confident, friendly tone",
      "Review this list of steps for anything missing",
    ],
  },
];

/** The library the autocomplete searches while someone types. */
export const PROMPT_LIBRARY = PROMPT_GROUPS.flatMap((g) => g.items);

/** Up to `limit` library prompts that contain what was typed (case-insensitive), excluding an exact match. */
export function suggestFor(typed: string, limit = 4): string[] {
  const q = typed.trim().toLowerCase();
  if (q.length < 2) return [];
  return PROMPT_LIBRARY.filter((p) => p.toLowerCase().includes(q) && p.toLowerCase() !== q).slice(
    0,
    limit,
  );
}
