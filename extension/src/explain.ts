import type { Action } from "./detect/policy";

/** What the person reads. Every card says what happened, why, and what to do instead. */
export const CATEGORY_LABEL: Record<string, string> = {
  greek_id: "a Greek ID number (tax, social security or similar)",
  iban: "a bank account number (IBAN)",
  card: "a payment card number",
  secret: "a password or API key",
  person_email_phone: "personal contact details",
  client_name: "a client name",
  source_code: "source code",
  injection: "hidden instructions aimed at the AI",
  honeytoken: "a decoy credential from a protected document",
};

export function label(category: string): string {
  return CATEGORY_LABEL[category] ?? category.replaceAll("_", " ");
}

export function titleFor(action: Action): string {
  return {
    allow: "Looks fine",
    mask: "Sensitive values hidden",
    warn: "Check before you send",
    local: "Use the company AI for this",
    block: "This was not sent",
  }[action];
}

export function reasonsFor(action: Action, categories: string[], document?: string): string[] {
  const names = [...new Set(categories)].map(label);
  const list = document
    ? `text from the document "${document}"${names.length ? `, and ${names.join(", ")}` : ""}`
    : names.length
      ? names.join(", ")
      : "sensitive content";
  switch (action) {
    case "mask":
      return [
        `Your message contains ${list}.`,
        "Pyli replaced the values with placeholders before sending. The AI never sees the real values, and they come back in the answer on this page only.",
      ];
    case "warn":
      return [
        `Your message may contain ${list}.`,
        "Company policy asks you to confirm before it goes to an outside AI tool. Remove it, or send anyway and say why.",
      ];
    case "local":
      return [
        `Your message contains or resembles ${list}.`,
        "It stays inside the company if you ask the company AI instead. Same question, same answer quality for this task.",
      ];
    case "block":
      return [
        `Your message contains ${list}.`,
        "Company policy does not allow this to be sent to an outside AI tool. Ask the data owner, or use the company AI with a shorter excerpt.",
      ];
    default:
      return [];
  }
}
