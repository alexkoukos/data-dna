export interface DemoUser {
  user: string;
  team: string;
}

export interface PairingCode {
  code: string;
  user: string;
  team: string;
  expires_in: number;
}

export type Lang = "en" | "el";

export interface Sample {
  id: string;
  outcome: "allow" | "mask" | "warn" | "local" | "block";
  title: string;
  shows: string;
}

/** The five ready-to-paste texts. The files live in /samples (copied from the repo's samples/). */
export const SAMPLES: Sample[] = [
  {
    id: "1-allow",
    outcome: "allow",
    title: "An ordinary question",
    shows: "Nothing happens and nothing slows you down.",
  },
  {
    id: "2-mask",
    outcome: "mask",
    title: "A tax number and an IBAN",
    shows: "They are replaced before sending. The answer shows them again, on your page only.",
  },
  {
    id: "3-warn",
    outcome: "warn",
    title: "A client name",
    shows: "A card asks you to confirm and say why.",
  },
  {
    id: "4-redirect",
    outcome: "local",
    title: "Text from a confidential document",
    shows: "The card offers the company AI, so the text stays inside.",
  },
  {
    id: "5-block",
    outcome: "block",
    title: "The board memo",
    shows: "It is not sent. You see why, and what to do instead.",
  },
];

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as T;
}

export const fetchDemoUsers = () => getJson<DemoUser[]>("/v1/demo-users");

export const createPairingCode = (user: string) =>
  getJson<PairingCode>("/v1/pair/code", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user }),
  });

export async function fetchSample(id: string, lang: Lang): Promise<string> {
  const res = await fetch(`/samples/${lang}/${id}.txt`);
  if (!res.ok) throw new Error("sample not found");
  return (await res.text()).trim();
}

/** The demo chat runs next to the dashboard, on port 3100. */
export const mockAiUrl = () => `${window.location.protocol}//${window.location.hostname}:3100`;
