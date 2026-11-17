import type { Adapter } from "./types";
import { readText, writeText } from "./dom";

export const mockAi: Adapter = {
  id: "mock-ai",
  tool: "Mock AI (demo)",
  matches: (u) => u.hostname === "localhost" && u.port === "3100",
  getComposer: () => document.querySelector<HTMLElement>("#prompt"),
  getText() {
    return readText(this.getComposer());
  },
  setText(text) {
    return writeText(this.getComposer(), text);
  },
  getSendButton: () => document.querySelector<HTMLElement>("#send"),
  responseRoot: () => document.querySelector<HTMLElement>("#messages") ?? document.body,
};
