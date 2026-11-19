import type { Adapter } from "./types";
import { readText, writeText } from "./dom";

export const chatgpt: Adapter = {
  id: "chatgpt",
  tool: "ChatGPT",
  matches: (u) => u.hostname === "chatgpt.com" || u.hostname === "chat.openai.com",
  getComposer: () =>
    document.querySelector<HTMLElement>("#prompt-textarea") ??
    document.querySelector<HTMLElement>('div[contenteditable="true"]'),
  getText() {
    return readText(this.getComposer());
  },
  setText(text) {
    return writeText(this.getComposer(), text);
  },
  getSendButton: () =>
    document.querySelector<HTMLElement>('button[data-testid="send-button"]') ??
    document.querySelector<HTMLElement>('button[aria-label="Send prompt"]'),
  responseRoot: () => document.querySelector<HTMLElement>("main") ?? document.body,
};
