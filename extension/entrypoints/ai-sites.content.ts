import { adapterFor } from "../src/adapters";
import type { Adapter } from "../src/adapters/types";
import { runCheck } from "../src/check";
import { scan } from "../src/detect/engine";
import { DEFAULT_POLICY, type Policy } from "../src/detect/policy";
import { label, titleFor } from "../src/explain";
import { Overlay } from "../src/overlay";
import type { CheckResult, Msg } from "../src/types";
import { Unmasker } from "../src/unmask";

function send<T>(msg: Msg): Promise<T | null> {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(msg, (res) =>
        resolve(chrome.runtime.lastError ? null : (res as T)),
      );
    } catch {
      resolve(null);
    }
  });
}

export default defineContentScript({
  matches: [
    "http://localhost:3100/*",
    "https://chatgpt.com/*",
    "https://chat.openai.com/*",
    "https://claude.ai/*",
    "https://gemini.google.com/*",
  ],
  runAt: "document_idle",
  main() {
    const adapter = adapterFor(new URL(location.href));
    if (!adapter) return;
    const overlay = new Overlay();
    const unmasker = new Unmasker();
    let policy: Policy = DEFAULT_POLICY;
    let bypass = false;
    let busy = false;

    void send<Policy>({ type: "policy" }).then((p) => {
      if (p) policy = p;
      banIfNeeded();
    });
    void send({ type: "visit", tool: adapter.tool });
    unmasker.start(adapter.responseRoot());

    function banIfNeeded() {
      const entry = policy.tools[adapter!.tool];
      if (entry?.approval === "unapproved") {
        const alt = entry.alternative ?? "the company AI";
        overlay.banner(`${adapter!.tool} is not approved here. Use ${alt} instead.`, {
          label: "Open company AI",
          onClick: () => void send({ type: "openPanel", prompt: "" }),
        });
      }
    }

    // While typing or pasting: tell the person early, change nothing.
    document.addEventListener(
      "paste",
      (e) => {
        const composer = adapter.getComposer();
        if (!composer || !(e.target instanceof Node) || !composer.contains(e.target)) return;
        const text = e.clipboardData?.getData("text/plain") ?? "";
        if (!text) return;
        const s = scan(text);
        const n = new Set(s.findings.map((f) => f.value)).size;
        if (n > 0) {
          const kinds = [...new Set(s.findings.map((f) => label(f.category)))].join(", ");
          overlay.chip(
            `${n} sensitive item${n > 1 ? "s" : ""} found (${kinds}). You will be asked before sending.`,
          );
        }
      },
      true,
    );

    async function guard(e: Event) {
      if (bypass) return;
      if (busy) {
        // A check is already running: do not let a second send slip past it.
        e.preventDefault();
        e.stopImmediatePropagation();
        return;
      }
      const text = adapter!.getText();
      if (!text.trim()) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      busy = true;
      try {
        overlay.clearChip();
        const result = await runCheck(text, policy, (t) =>
          send<Partial<CheckResult>>({
            type: "l2",
            text: t,
            tool: adapter!.tool,
            url: location.href,
          }),
        );
        await handle(adapter!, text, result);
      } finally {
        busy = false;
      }
    }

    function resubmit(a: Adapter) {
      bypass = true;
      const button = a.getSendButton();
      if (button && !(button as HTMLButtonElement).disabled) {
        button.click();
      } else {
        a.getComposer()?.dispatchEvent(
          new KeyboardEvent("keydown", {
            key: "Enter",
            code: "Enter",
            bubbles: true,
            cancelable: true,
          }),
        );
      }
      window.setTimeout(() => (bypass = false), 80);
    }

    async function handle(a: Adapter, original: string, r: CheckResult) {
      const category = r.findings[0]?.category;
      void send({ type: "event", tool: a.tool, action: r.action, category });
      const note =
        r.source === "offline" ? " (company server not reached, checked in your browser only)" : "";

      if (r.action === "allow") {
        resubmit(a);
        return;
      }

      if (r.action === "mask") {
        const masked = r.maskedText;
        if (!masked || !r.placeholders || !a.setText(masked)) {
          // We could not rewrite the composer safely, so we do not send the original.
          await overlay.card({
            action: "warn",
            title: "Could not hide the values",
            reasons: [
              "Pyli found sensitive values but could not replace them in this page, so nothing was sent.",
              "Remove the values yourself, then send again.",
            ],
            buttons: [{ id: "edit", label: "Edit message", kind: "primary" }],
          });
          return;
        }
        unmasker.remember(r.placeholders);
        const n = Object.keys(r.placeholders).length;
        resubmit(a);
        overlay.note(
          `${n} item${n > 1 ? "s" : ""} masked before sending. Real values return in the answer, on this page only.${note}`,
        );
        return;
      }

      const details = r.findings.map((f) => `${label(f.category)}: ${f.preview}`);
      if (r.document)
        details.unshift(`Looks like "${r.document.title}" (${r.document.sensitivity}).`);

      if (r.action === "warn") {
        const choice = await overlay.card({
          action: "warn",
          title: titleFor("warn"),
          reasons: [...r.reasons, ...(note ? [note.trim()] : [])],
          details,
          askReason: true,
          preview: r.rewrite ? { label: "Safer version", text: r.rewrite } : undefined,
          buttons: [
            { id: "edit", label: "Edit message", kind: "secondary" },
            ...(r.rewrite
              ? [{ id: "rewrite", label: "Use safer version", kind: "primary" as const }]
              : []),
            { id: "send", label: "Send anyway", kind: "danger" },
          ],
        });
        if (choice.id === "rewrite" && r.rewrite) {
          if (a.setText(r.rewrite)) resubmit(a);
        } else if (choice.id === "send") {
          void send({ type: "override", tool: a.tool, reason: choice.reason || "no reason given" });
          resubmit(a);
        }
        return;
      }

      if (r.action === "local") {
        const choice = await overlay.card({
          action: "local",
          title: titleFor("local"),
          reasons: r.reasons,
          details,
          buttons: [
            { id: "edit", label: "Edit message", kind: "secondary" },
            { id: "ask", label: "Ask the company AI", kind: "primary" },
          ],
        });
        if (choice.id === "ask") void send({ type: "openPanel", prompt: original });
        return;
      }

      await overlay
        .card({
          action: "block",
          title: titleFor("block"),
          reasons: r.reasons,
          details: [...details, `Policy version ${r.policyVersion ?? 0}.`],
          buttons: [
            { id: "edit", label: "Edit message", kind: "secondary" },
            { id: "ask", label: "Open company AI", kind: "primary" },
          ],
        })
        .then((c) => {
          if (c.id === "ask") void send({ type: "openPanel", prompt: "" });
        });
    }

    document.addEventListener(
      "keydown",
      (e) => {
        if (e.key !== "Enter" || e.shiftKey || e.isComposing) return;
        const composer = adapter.getComposer();
        if (!composer || !(e.target instanceof Node) || !composer.contains(e.target)) return;
        void guard(e);
      },
      true,
    );
    document.addEventListener(
      "click",
      (e) => {
        const button = adapter.getSendButton();
        if (button && e.target instanceof Node && button.contains(e.target)) void guard(e);
      },
      true,
    );
  },
});
