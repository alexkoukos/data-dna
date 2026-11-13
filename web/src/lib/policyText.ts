import type { Decision } from "./securityApi";

/** Plain-words names and effects for the policy editor. */

export const ACTIONS: { id: Decision; label: string }[] = [
  { id: "allow", label: "Allow" },
  { id: "mask", label: "Mask" },
  { id: "warn", label: "Warn" },
  { id: "local", label: "Answer locally" },
  { id: "block", label: "Block" },
];

export const EFFECT: Record<Decision, string> = {
  allow: "The message goes through unchanged. Nothing is hidden or asked.",
  mask: "The sensitive value is swapped for a placeholder before it leaves. The answer is restored for the sender only.",
  warn: "The sender is stopped and must give a reason before sending anyway. The reason is logged.",
  local:
    "The message is answered by the model on company hardware. It never goes to a cloud model.",
  block: "The message is not sent. The sender sees why and which approved tool to use instead.",
};

export const CATEGORY_TEXT: Record<string, { label: string; about: string }> = {
  greek_id: {
    label: "Greek ID numbers",
    about: "Tax numbers (AFM) and social security numbers (AMKA).",
  },
  iban: {
    label: "Bank account numbers",
    about: "IBANs, including ones written with spaces or odd characters.",
  },
  card: { label: "Payment cards", about: "Card numbers that pass the Luhn check." },
  secret: { label: "Secrets and keys", about: "API keys, tokens and passwords." },
  person_email_phone: {
    label: "Personal contact details",
    about: "Names, emails and phone numbers.",
  },
  client_name: { label: "Client names", about: "Names of the company's clients." },
  source_code: { label: "Source code", about: "Code from company repositories." },
  injection: { label: "Prompt injection", about: "Text that tries to take control of the AI." },
};

export const SENSITIVITY_TEXT: Record<string, { label: string; about: string }> = {
  internal: { label: "Internal documents", about: "Not secret, but not for outside tools." },
  confidential: {
    label: "Confidential documents",
    about: "Contracts, strategy and client material.",
  },
  restricted: {
    label: "Restricted documents",
    about: "The crown jewels. Even a rewritten copy is caught.",
  },
};

export function textFor(scope: "category" | "sensitivity", key: string) {
  const table = scope === "category" ? CATEGORY_TEXT : SENSITIVITY_TEXT;
  return table[key] ?? { label: key.replace(/_/g, " "), about: "" };
}
