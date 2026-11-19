import type { Action } from "./detect/policy";

export interface FindingView {
  entity: string;
  category: string;
  /** Masked preview, never the real value. */
  preview: string;
}

export interface CheckResult {
  action: Action;
  /** Plain-language lines: what happened and why. */
  reasons: string[];
  /** The server's own short reasons (which checks fired), shown under the plain-language text. */
  why?: string[];
  findings: FindingView[];
  /** Where the answer came from: the browser alone, the company server, or the browser because the server was down. */
  source: "l1" | "l2" | "offline";
  /** For mask: the text to put in the composer, and placeholder to real value (kept in this tab only). */
  maskedText?: string;
  placeholders?: Record<string, string>;
  /** For warn: a safer version of the prompt. */
  rewrite?: string;
  /** For local and block: which document this looks like. */
  document?: { title: string; sensitivity: string; coverage?: number };
  /** The approved path to suggest. */
  alternative?: string;
  policyVersion?: number;
}

export interface Settings {
  brainUrl: string;
  token: string;
  demoUser: string;
  userLabel: string;
}

export const DEFAULT_SETTINGS: Settings = {
  brainUrl: "http://localhost:8001",
  token: "",
  demoUser: "",
  userLabel: "",
};

/** Messages from the page scripts to the service worker. */
export type Msg =
  | {
      type: "l2";
      text: string;
      tool: string;
      url: string;
      attachments?: { filename: string; content_base64: string }[];
    }
  | {
      type: "event";
      tool: string;
      host: string;
      action: string;
      category?: string;
      offline?: boolean;
    }
  | { type: "visit"; tool: string; host: string }
  | { type: "openPanel"; prompt: string }
  | { type: "askLocal"; prompt: string }
  | { type: "override"; reason: string; tool: string; host: string }
  | { type: "policy"; force?: boolean }
  | { type: "stats" };
