// The four scenes of the hero loop. Everything here is invented demo data: fake names, fake
// salaries, a sample IBAN, a tax ID with a valid check digit but no owner, and a made-up key.

/** A plain string, or a sensitive value that turns into a masked token. */
export type Seg = string | { raw: string; pill: string };

export type Outcome = "mask" | "block" | "local";

export const OUTCOME_LABEL: Record<Outcome, string> = {
  mask: "Masked",
  block: "Blocked",
  local: "Answered locally",
};

export type Scene = {
  id: string;
  /** Short caption under the laptop. */
  caption: string;
  /** Read by screen readers only. */
  demoNote: string;
  site: { name: string; host: string; tab: string };
  prompt: string;
  /** Pasted lines. A line with several cells is a table row. */
  paste: Seg[][];
  /** Monospace for pasted code. */
  mono?: boolean;
  /** A dragged-in document instead of pasted text. */
  file?: { name: string; meta: string };
  outcome: Outcome;
  card: {
    headline: string;
    body: string;
    tip: string;
    primary: string;
    secondary: string;
    /** The cleaned question, shown when the sentinel removed a secret and rewrote the message. */
    rewrite?: string;
  };
  /** Positions inside the 720 x 450 screen, tuned by eye. */
  geo: {
    sentinel: [number, number];
    perch: [number, number];
    cursorType: [number, number];
    cursorCard: [number, number];
  };
};

export const SCENES: Scene[] = [
  {
    id: "payroll",
    caption: "Pasting payroll into a public AI",
    demoNote: "Demo data: the names and salaries on screen are invented.",
    site: { name: "AI Chat", host: "ai-chat.example", tab: "AI Chat" },
    prompt: "make this table nicer for the board",
    paste: [
      ["Name", "Role", "Salary"],
      [
        { raw: "Elena Marlowe", pill: "[PERSON_1]" },
        "Senior Consultant",
        { raw: "€84,000", pill: "[SALARY_1]" },
      ],
      [
        { raw: "Jonas Vickery", pill: "[PERSON_2]" },
        "Team Lead",
        { raw: "€96,500", pill: "[SALARY_2]" },
      ],
      [
        { raw: "Priya Danbury", pill: "[PERSON_3]" },
        "Analyst",
        { raw: "€58,200", pill: "[SALARY_3]" },
      ],
    ],
    outcome: "mask",
    card: {
      headline: "That's company data. I kept it in.",
      body: "Salaries and names were replaced before anything was sent.",
      tip: "Next time: Company AI can read this table safely.",
      primary: "Send to Company AI",
      secondary: "Send masked version",
    },
    geo: { sentinel: [330, 262], perch: [388, 42], cursorType: [210, 388], cursorCard: [166, 204] },
  },
  {
    id: "bank",
    caption: "Sending bank details to a public AI",
    demoNote: "Demo data: the IBAN and tax ID are invented and belong to no one.",
    site: { name: "Ask AI", host: "ask-ai.example", tab: "Ask AI" },
    prompt: "write a payment reminder to this supplier",
    paste: [
      ["Supplier: Aegean Packaging SA"],
      ["IBAN: ", { raw: "GR16 0110 1250 0000 0001 2300 695", pill: "[IBAN_1]" }],
      ["AFM: ", { raw: "123456783", pill: "[TAX_ID_1]" }],
    ],
    outcome: "block",
    card: {
      headline: "Bank details stay inside.",
      body: "I stopped this send. An IBAN and a tax ID don't go to public AI tools.",
      tip: "Use Company AI, it can see this safely.",
      primary: "Open Company AI",
      secondary: "Edit message",
    },
    geo: { sentinel: [330, 290], perch: [388, 66], cursorType: [200, 392], cursorCard: [158, 228] },
  },
  {
    id: "key",
    caption: "Pasting a live API key into a code assistant",
    demoNote: "Demo data: the key on screen is invented and opens nothing.",
    site: { name: "Code Helper", host: "code-helper.example", tab: "Code Helper" },
    prompt: "why does this return 401? please fix it",
    paste: [
      ["PORT=8080"],
      ["PAYMENTS_URL=https://pay.internal"],
      ["API_KEY=", { raw: "sk-demo-4f9aQ2bX7LmN8vT3", pill: "[API_KEY_1]" }],
    ],
    mono: true,
    outcome: "block",
    card: {
      headline: "Keys never leave the company.",
      body: "I removed it. Here's your question without it:",
      rewrite: "why does this return 401? … API_KEY=[API_KEY_1]",
      tip: "Rotate the key if it was ever shared before.",
      primary: "Send without the key",
      secondary: "Edit message",
    },
    geo: { sentinel: [330, 290], perch: [388, 62], cursorType: [220, 392], cursorCard: [172, 234] },
  },
  {
    id: "memo",
    caption: "Dragging in a confidential board memo",
    demoNote: "Demo data: the board memo is an invented file with no real content.",
    site: { name: "AI Chat", host: "ai-chat.example", tab: "AI Chat" },
    prompt: "summarise this for me",
    paste: [],
    file: { name: "Q4-board-memo.pdf", meta: "PDF · 12 pages · Confidential" },
    outcome: "local",
    card: {
      headline: "Answered by Company AI.",
      body: "Confidential, so it was read on our own servers.",
      tip: "Confidential documents never go to public tools.",
      primary: "Read the answer",
      secondary: "Why?",
    },
    geo: { sentinel: [330, 300], perch: [388, 82], cursorType: [200, 394], cursorCard: [146, 224] },
  },
];
