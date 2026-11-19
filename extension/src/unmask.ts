/**
 * Puts the real values back into the AI's answer, in the page only. The map lives in memory in
 * this tab, is never saved, and disappears when the tab closes.
 */
const TOKEN = /\[[A-Z0-9_]+_\d+\]/g;

export class Unmasker {
  private map = new Map<string, string>();
  private observer: MutationObserver | null = null;

  remember(placeholders: Record<string, string>) {
    for (const [k, v] of Object.entries(placeholders)) this.map.set(k, v);
  }

  get size() {
    return this.map.size;
  }

  start(root: HTMLElement) {
    this.observer?.disconnect();
    this.observer = new MutationObserver((records) => {
      for (const r of records) {
        if (r.type === "characterData") this.walk(r.target);
        r.addedNodes.forEach((n) => this.walk(n));
      }
    });
    this.observer.observe(root, { childList: true, subtree: true, characterData: true });
    this.walk(root);
  }

  stop() {
    this.observer?.disconnect();
  }

  walk(node: Node) {
    if (this.map.size === 0) return;
    if (node.nodeType === Node.TEXT_NODE) {
      this.replaceIn(node as Text);
      return;
    }
    if (!(node instanceof HTMLElement)) return;
    if (node.closest('hive-overlay, textarea, [contenteditable="true"], .sentry-restored')) return;
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    const texts: Text[] = [];
    while (walker.nextNode()) texts.push(walker.currentNode as Text);
    texts.forEach((t) => this.replaceIn(t));
  }

  private replaceIn(text: Text) {
    const parent = text.parentElement;
    if (
      !parent ||
      parent.closest('.sentry-restored, textarea, [contenteditable="true"], hive-overlay')
    )
      return;
    const value = text.data;
    if (!value.includes("[")) return;
    const frag = document.createDocumentFragment();
    let last = 0;
    let changed = false;
    for (const m of value.matchAll(TOKEN)) {
      const real = this.map.get(m[0]);
      if (real === undefined) continue;
      changed = true;
      const idx = m.index ?? 0;
      frag.append(value.slice(last, idx));
      const span = document.createElement("span");
      span.className = "hive-restored";
      span.textContent = real;
      span.title = "Restored on this page only. The AI never saw this value.";
      span.style.cssText = "text-decoration: underline dotted; text-underline-offset: 3px;";
      frag.append(span);
      last = idx + m[0].length;
    }
    if (!changed) return;
    frag.append(value.slice(last));
    text.replaceWith(frag);
  }
}
