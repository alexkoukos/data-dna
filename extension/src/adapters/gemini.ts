import type { Adapter } from "./types";
import { readText, writeText } from "./dom";

export const gemini: Adapter = {
  id: "gemini",
  tool: "Gemini",
  matches: (u) => u.hostname === "gemini.google.com",
  getComposer: () =>
    document.querySelector<HTMLElement>("rich-textarea .ql-editor") ??
    document.querySelector<HTMLElement>('div[contenteditable="true"]'),
  getText() {
    return readText(this.getComposer());
  },
  setText(text) {
    return writeText(this.getComposer(), text);
  },
  getSendButton: () =>
    document.querySelector<HTMLElement>("button.send-button") ??
    document.querySelector<HTMLElement>('button[aria-label="Send message"]'),
  responseRoot: () => document.querySelector<HTMLElement>("main") ?? document.body,
};
