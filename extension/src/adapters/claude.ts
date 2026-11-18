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
  getSendButton() {
    // Look next to the composer first, then anywhere: the label changes between releases.
    const scope = this.getComposer()?.closest("fieldset, form") ?? document;
    const find = (root: ParentNode) =>
      root.querySelector<HTMLElement>('button[aria-label*="send" i]:not([disabled])') ??
      root.querySelector<HTMLElement>('button[type="submit"]:not([disabled])');
    return find(scope) ?? find(document);
  },
  responseRoot: () => document.querySelector<HTMLElement>("main") ?? document.body,
};
