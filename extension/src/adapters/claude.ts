import type { Adapter } from "./types";
import { readText, writeText } from "./dom";

export const claude: Adapter = {
  id: "claude",
  tool: "Claude.ai",
  matches: (u) => u.hostname === "claude.ai",
  getComposer: () =>
    document.querySelector<HTMLElement>('div.ProseMirror[contenteditable="true"]') ??
    document.querySelector<HTMLElement>('div[contenteditable="true"]'),
  getText() {
    return readText(this.getComposer());
  },
  setText(text) {
    return writeText(this.getComposer(), text);
  },
  getSendButton: () =>
    document.querySelector<HTMLElement>('button[aria-label="Send message"]') ??
    document.querySelector<HTMLElement>('button[aria-label="Send Message"]'),
  responseRoot: () => document.querySelector<HTMLElement>("main") ?? document.body,
};
