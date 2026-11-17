import type { Action } from "./detect/policy";

/**
 * Everything the person sees on top of an AI site. It lives in a Shadow DOM so the site's CSS
 * cannot break it and ours cannot leak into the site.
 */
const STYLE = `
:host { all: initial; }
* { box-sizing: border-box; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
.layer { position: fixed; inset: 0; pointer-events: none; z-index: 2147483647; }
.card, .chip, .banner, .note { pointer-events: auto; }
.card {
  position: absolute; left: 50%; bottom: 96px; transform: translateX(-50%);
  width: min(460px, calc(100vw - 32px)); background: #fff; color: #1b2430;
  border-radius: 14px; box-shadow: 0 12px 40px rgba(16,24,40,.28), 0 2px 6px rgba(16,24,40,.12);
  padding: 16px 18px 14px; border-top: 5px solid var(--accent);
  animation: rise .16s ease-out;
}
@keyframes rise { from { opacity: 0; transform: translate(-50%, 8px); } to { opacity: 1; transform: translate(-50%, 0); } }
@media (prefers-reduced-motion: reduce) { .card { animation: none; } }
.head { display: flex; align-items: center; gap: 10px; }
.badge { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700;
  letter-spacing: .02em; text-transform: uppercase; color: var(--accent-text); background: var(--accent-bg);
  border-radius: 6px; padding: 3px 8px; }
h2 { margin: 8px 0 4px; font-size: 17px; line-height: 1.3; font-weight: 700; }
p { margin: 0 0 6px; font-size: 14px; line-height: 1.5; color: #3a4658; }
ul { margin: 6px 0 8px; padding-left: 18px; font-size: 13px; color: #3a4658; }
code { font-family: ui-monospace, Menlo, Consolas, monospace; background: #eef1f5; border-radius: 4px; padding: 1px 5px; font-size: 12px; }
label { display: block; font-size: 12px; font-weight: 600; margin: 10px 0 4px; color: #3a4658; }
textarea { width: 100%; min-height: 54px; resize: vertical; font-size: 14px; padding: 8px 10px;
  border: 1px solid #b8c1cf; border-radius: 8px; color: inherit; background: #fff; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; margin-top: 12px; }
button { min-height: 44px; padding: 0 16px; border-radius: 10px; font-size: 14px; font-weight: 600;
  cursor: pointer; border: 1px solid #b8c1cf; background: #fff; color: #1b2430; }
button.primary { background: #1f4fd8; border-color: #1f4fd8; color: #fff; }
button.danger { background: #fff; border-color: #b42318; color: #b42318; }
button:focus-visible, textarea:focus-visible, a:focus-visible { outline: 3px solid #1f4fd8; outline-offset: 2px; }
.chip { position: absolute; left: 50%; bottom: 96px; transform: translateX(-50%); background: #1b2430; color: #fff;
  font-size: 13px; padding: 8px 14px; border-radius: 999px; box-shadow: 0 6px 20px rgba(16,24,40,.3); }
.banner { position: absolute; top: 0; left: 0; right: 0; background: #fff4e5; color: #6b3a00; border-bottom: 2px solid #f59e0b;
  padding: 10px 16px; font-size: 14px; display: flex; gap: 12px; align-items: center; justify-content: center; flex-wrap: wrap; }
.banner button { min-height: 32px; padding: 0 12px; }
.note { position: absolute; right: 16px; bottom: 16px; max-width: 320px; background: #eaf6ee; color: #14532d; border: 1px solid #86c99b;
  border-radius: 10px; padding: 8px 12px; font-size: 13px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
@media (prefers-color-scheme: dark) {
  .card { background: #182130; color: #e8edf5; } p, ul, label { color: #b9c4d6; }
  code { background: #243047; } textarea, button { background: #1f2a3d; color: #e8edf5; border-color: #3b4a63; }
  button.primary { background: #4c7dff; border-color: #4c7dff; color: #0b1220; }
  button.danger { color: #ff8a80; border-color: #ff8a80; }
}
`;

const ACCENT: Record<
  Action,
  { accent: string; text: string; bg: string; icon: string; word: string }
> = {
  allow: { accent: "#16794a", text: "#0d4a2d", bg: "#dff5e8", icon: "✓", word: "Allowed" },
  mask: { accent: "#6d3fd1", text: "#3f1d8f", bg: "#ece4fb", icon: "▮", word: "Masked" },
  warn: { accent: "#c77700", text: "#6b3a00", bg: "#ffeccc", icon: "!", word: "Check first" },
  local: { accent: "#0b7a8a", text: "#064b55", bg: "#d7f1f5", icon: "⌂", word: "Company AI" },
  block: { accent: "#b42318", text: "#7a1710", bg: "#fde3e0", icon: "×", word: "Blocked" },
};

export interface CardButton {
  id: string;
  label: string;
  kind?: "primary" | "danger" | "secondary";
}

export interface CardOptions {
  action: Action;
  title: string;
  reasons: string[];
  details?: string[];
  buttons: CardButton[];
  askReason?: boolean;
  /** Placed under the details, e.g. a safer rewrite. */
  preview?: { label: string; text: string };
}

export interface CardChoice {
  id: string;
  reason: string;
}

export class Overlay {
  private host: HTMLElement;
  private root: ShadowRoot;
  private layer: HTMLElement;
  private live: HTMLElement;
  private chipTimer = 0;
  private lastFocus: Element | null = null;

  constructor() {
    this.host = document.createElement("pyli-overlay");
    this.root = this.host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = STYLE;
    this.layer = document.createElement("div");
    this.layer.className = "layer";
    this.live = document.createElement("div");
    this.live.className = "sr";
    this.live.setAttribute("aria-live", "polite");
    this.root.append(style, this.layer, this.live);
    document.documentElement.append(this.host);
  }

  private announce(text: string) {
    this.live.textContent = "";
    window.setTimeout(() => (this.live.textContent = text), 30);
  }

  /** Small notice under the composer: "2 items will be masked". */
  chip(text: string, ms = 6000) {
    this.layer.querySelector(".chip")?.remove();
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = text;
    this.layer.append(chip);
    this.announce(text);
    window.clearTimeout(this.chipTimer);
    this.chipTimer = window.setTimeout(() => chip.remove(), ms);
  }

  clearChip() {
    this.layer.querySelector(".chip")?.remove();
  }

  /** Quiet confirmation after a send, bottom right. */
  note(text: string, ms = 5000) {
    this.layer.querySelector(".note")?.remove();
    const el = document.createElement("div");
    el.className = "note";
    el.textContent = text;
    this.layer.append(el);
    this.announce(text);
    window.setTimeout(() => el.remove(), ms);
  }

  banner(text: string, action?: { label: string; onClick: () => void }) {
    this.layer.querySelector(".banner")?.remove();
    const el = document.createElement("div");
    el.className = "banner";
    el.setAttribute("role", "status");
    const span = document.createElement("span");
    span.textContent = text;
    el.append(span);
    if (action) {
      const b = document.createElement("button");
      b.textContent = action.label;
      b.addEventListener("click", action.onClick);
      el.append(b);
    }
    this.layer.append(el);
  }

  /** Shows a card and resolves with the button the person chose. Esc counts as "edit". */
  card(opts: CardOptions): Promise<CardChoice> {
    this.layer.querySelector(".card")?.remove();
    this.lastFocus = document.activeElement;
    const a = ACCENT[opts.action];
    const el = document.createElement("div");
    el.className = "card";
    el.style.setProperty("--accent", a.accent);
    el.style.setProperty("--accent-text", a.text);
    el.style.setProperty("--accent-bg", a.bg);
    el.setAttribute("role", "alertdialog");
    el.setAttribute("aria-modal", "true");
    el.setAttribute("aria-labelledby", "pyli-title");
    el.setAttribute("aria-describedby", "pyli-desc");

    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = `${a.icon} ${a.word}`;
    const head = document.createElement("div");
    head.className = "head";
    head.append(badge);
    const h2 = document.createElement("h2");
    h2.id = "pyli-title";
    h2.textContent = opts.title;
    const desc = document.createElement("div");
    desc.id = "pyli-desc";
    for (const line of opts.reasons) {
      const p = document.createElement("p");
      p.textContent = line;
      desc.append(p);
    }
    el.append(head, h2, desc);

    if (opts.details?.length) {
      const ul = document.createElement("ul");
      for (const d of opts.details) {
        const li = document.createElement("li");
        li.textContent = d;
        ul.append(li);
      }
      el.append(ul);
    }
    if (opts.preview) {
      const lab = document.createElement("label");
      lab.textContent = opts.preview.label;
      const code = document.createElement("code");
      code.textContent = opts.preview.text;
      el.append(lab, code);
    }
    let reasonBox: HTMLTextAreaElement | null = null;
    if (opts.askReason) {
      const lab = document.createElement("label");
      lab.htmlFor = "pyli-reason";
      lab.textContent = "Why do you need to send this? (saved with the log)";
      reasonBox = document.createElement("textarea");
      reasonBox.id = "pyli-reason";
      el.append(lab, reasonBox);
    }
    const actions = document.createElement("div");
    actions.className = "actions";
    el.append(actions);
    this.layer.append(el);
    this.announce(`${opts.title}. ${opts.reasons.join(" ")}`);

    return new Promise<CardChoice>((resolve) => {
      const done = (id: string) => {
        el.remove();
        document.removeEventListener("keydown", onKey, true);
        if (this.lastFocus instanceof HTMLElement) this.lastFocus.focus();
        resolve({ id, reason: reasonBox?.value.trim() ?? "" });
      };
      for (const b of opts.buttons) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = b.label;
        if (b.kind && b.kind !== "secondary") btn.className = b.kind;
        btn.addEventListener("click", () => done(b.id));
        actions.append(btn);
      }
      const focusables = () => [...el.querySelectorAll<HTMLElement>("button, textarea")];
      const onKey = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          done(opts.buttons.find((b) => b.id === "edit")?.id ?? "edit");
        } else if (e.key === "Tab") {
          const items = focusables();
          const first = items[0];
          const last = items[items.length - 1];
          const active = this.root.activeElement;
          if (!first || !last) return;
          if (e.shiftKey && active === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && active === last) {
            e.preventDefault();
            first.focus();
          }
        } else {
          // Keep keystrokes inside the card from reaching the AI site underneath.
          e.stopPropagation();
        }
      };
      document.addEventListener("keydown", onKey, true);
      (el.querySelector<HTMLElement>("button.primary") ?? focusables()[0])?.focus();
    });
  }
}
