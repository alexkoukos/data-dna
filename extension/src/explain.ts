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
    mask: "That's company data. I kept it in.",
    warn: "Let's check this before it leaves.",
    local: "Company AI can answer this safely.",
    block: "This stays inside the company.",
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
        "I replaced the values with placeholders before anything was sent. The AI never sees the real ones, and they come back in the answer on this page only.",
      ];
    case "warn":
      return [
        `Your message may contain ${list}.`,
        "Company policy asks you to confirm before this goes to an outside AI tool. Next time: remove it, or send anyway and say why.",
      ];
    case "local":
      return [
        `Your message contains or resembles ${list}.`,
        "Next time: Company AI can read this safely. Same question, answered on our own servers.",
      ];
    case "block":
      return [
        `Your message contains ${list}.`,
        "I stopped this send. Next time: use Company AI, which can see this safely, or ask the data owner.",
      ];
    default:
      return [];
  }
}
