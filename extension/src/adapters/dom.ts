/** Shared helpers for reading and writing a composer, textarea or contenteditable. */
export function readText(el: HTMLElement | null): string {
  if (!el) return "";
  if (el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) return el.value;
  return el.innerText.replace(/ /g, " ").replace(/\n$/, "");
}

export function writeText(el: HTMLElement | null, text: string): boolean {
  if (!el) return false;
  el.focus();
  if (el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement : HTMLInputElement;
    Object.getOwnPropertyDescriptor(proto.prototype, "value")?.set?.call(el, text);
    el.dispatchEvent(
      new InputEvent("input", { bubbles: true, inputType: "insertText", data: text }),
    );
  } else {
    // ProseMirror and similar editors listen to real editing commands, not to innerText.
    document.execCommand("selectAll", false);
    if (!document.execCommand("insertText", false, text)) {
      el.textContent = text;
      el.dispatchEvent(
        new InputEvent("input", { bubbles: true, inputType: "insertText", data: text }),
      );
    }
  }
  return readText(el).trim() === text.trim();
}
