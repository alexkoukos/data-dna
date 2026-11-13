import type { Outcome } from "../components/OutcomeChip";

const WHAT: Record<string, string> = {
  "greek id": "a Greek ID number (AFM or AMKA)",
  iban: "a bank account number (IBAN)",
  card: "a payment card number",
  secret: "a password or access key",
  "person email phone": "personal contact details",
  "client name": "a client name",
  "source code": "source code",
  injection: "instructions that try to take over the assistant",
};

/** Turns a brain reason like "Contains iban" into a sentence a person understands. */
export function explainReason(reason: string): string {
  const contains = /^Contains (.+)$/.exec(reason);
  if (contains) {
    const what = WHAT[contains[1]];
    return what ? `Your message contains ${what}.` : `Your message contains ${contains[1]}.`;
  }
  const doc = /^Matches a (.+) document$/.exec(reason);
  if (doc) return `It matches a ${doc[1]} company document.`;
  if (reason.startsWith("Evasion attempt detected")) {
    return "Some characters were hidden or spaced out, which looks like an attempt to get past the checks.";
  }
  return reason;
}

/** What the gateway did about it, in plain words. */
export const WHAT_WE_DID: Record<Outcome, string> = {
  allow: "",
  mask: "We replaced it with a placeholder before sending, and put your original back in the answer.",
  local: "A model that runs inside the company answered, so the data did not leave.",
  warn: "We asked before sending.",
  block: "We did not send it.",
};
