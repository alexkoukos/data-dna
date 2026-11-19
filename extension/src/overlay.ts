import type { Action } from "./detect/policy";
import { TEXTURE_CSS } from "./texture";
import {
  Ban,
  Check,
  createElement,
  EyeOff,
  House,
  Pencil,
  SendHorizontal,
  ShieldCheck,
  TriangleAlert,
  type IconNode,
} from "lucide";

/**
 * Everything the person sees on top of an AI site. It lives in a Shadow DOM so the site's CSS
 * cannot break it and ours cannot leak into the site.
 */
const STYLE = `
:host { all: initial; }
* { box-sizing: border-box; font-family: 'Poppins', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.layer { position: fixed; inset: 0; pointer-events: none; z-index: 2147483647; }
.chip, .banner, .note { pointer-events: auto; }
.cardwrap { position: absolute; left: 50%; bottom: 96px; transform: translateX(-50%); width: min(540px, calc(100vw - 32px)); animation: rise .2s ease-out; pointer-events: none; }
.card::before { content: ""; display: block; height: 4px; background: var(--solid); }
.card {
  position: relative; background: #0e141c; color: #eaf0f7;
  border: 1px solid #e5e7eb; border-radius: 22px; overflow: hidden; pointer-events: auto;
  box-shadow: 0 24px 60px rgba(38,38,38,.22), 0 4px 14px rgba(38,38,38,.1);
}
/* Slow ribbons drift behind the content; they carry the outcome colour and stay subtle */
.ribbons { position: absolute; inset: 0; overflow: hidden; z-index: 0; pointer-events: none; }
.rib { position: absolute; left: 0; width: 200%; height: 120px; fill: none; stroke-width: 26; stroke-linecap: round; filter: blur(6px); }
.rib1 { top: -4%; stroke: var(--solid); opacity: .2; animation: flow 18s linear infinite; }
.rib2 { top: 34%; stroke: #22c5e8; opacity: .24; animation: flow 26s linear infinite reverse; }
.rib3 { top: 66%; stroke: #67dbf5; opacity: .3; animation: flow 32s linear infinite; }
@keyframes flow { to { transform: translateX(-50%); } }
@media (prefers-reduced-motion: reduce) { .rib { animation: none; } }
/* A second, smaller sentinel patrols the card's edge while the one in the header hovers and scans */
.patrol { position: absolute; inset: -22px; pointer-events: none; }
.psentinel { position: absolute; width: 30px; offset-path: inset(0 round 34px); offset-rotate: 0deg; offset-anchor: 50% 50%; animation: orbit 11s linear infinite; }
.psentinel span { display: block; animation: face 11s steps(1) infinite, bob .5s ease-in-out infinite alternate; }
@keyframes orbit { from { offset-distance: 0%; } to { offset-distance: 100%; } }
@keyframes face { 0% { transform: scaleX(1); } 50% { transform: scaleX(-1); } }
@keyframes bob { from { translate: 0 -2px; } to { translate: 0 2px; } }
/* The eye scans side to side while the body floats */
.sentinel .sentinel-eye { animation: scan 2.4s ease-in-out infinite; }
@keyframes scan { 0%,100% { transform: translateX(-5px); } 50% { transform: translateX(5px); } }
.head .sentinel { animation: hover 3.6s ease-in-out infinite; }
@keyframes hover { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
@media (prefers-reduced-motion: reduce) { .head .sentinel, .psentinel, .psentinel span, .sentinel .sentinel-eye { animation: none; } .patrol { display: none; } }
@keyframes rise { from { opacity: 0; transform: translate(-50%, 12px); } to { opacity: 1; transform: translate(-50%, 0); } }
@media (prefers-reduced-motion: reduce) { .cardwrap { animation: none; } }
/* Header band takes the outcome's colour, so the verdict is the first thing seen */
.head { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; padding: 22px 28px 18px; position: relative; z-index: 1; }
.sentinel { flex: none; width: 48px; }
.sentinel svg { display: block; width: 100%; height: auto; }
.head-text { min-width: 0; flex: 1; }
.chipo { flex: none; margin-left: auto; display: inline-flex; align-items: center; gap: 8px; font-family: 'Space Grotesk', 'Poppins', system-ui, sans-serif; font-size: 20px; line-height: 26px; font-weight: 600; color: var(--fg); white-space: nowrap; }
.chipo i { display: inline-flex; }
h2 { margin: 0; font-family: 'Space Grotesk', 'Poppins', system-ui, sans-serif; font-size: 22px; line-height: 29px; font-weight: 600; color: #262626; }
.main { position: relative; z-index: 1; padding: 4px 28px 28px; }
p { margin: 0; font-size: 15px; line-height: 23px; color: #525252; }
.found { margin: 16px 0 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; gap: 8px; }
.found li { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border: 1px solid rgba(38,38,38,.12); border-radius: 9999px; background: rgba(255,255,255,.6); font-size: 13px; line-height: 18px; color: #262626; font-weight: 600; }

.found li::before { content: ""; flex: none; width: 7px; height: 7px; border-radius: 9999px; background: var(--solid); }
code { font-family: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace; background: #f9fafb; border: 1px solid #e5e7eb;
  border-radius: 12px; padding: 12px 14px; font-size: 13px; line-height: 20px; color: #262626; display: block; margin: 6px 0 0; white-space: pre-wrap; }
label { display: block; font-size: 13px; font-weight: 800; margin: 20px 0 6px; color: #262626; }
.tip { margin: 16px 0 0; padding: 12px 14px; border-radius: 12px; background: rgba(255,255,255,.55); font-size: 14px; line-height: 21px; color: #525252; }
textarea { width: 100%; min-height: 72px; resize: vertical; font-size: 14px; line-height: 21px; padding: 12px 14px;
  border: 1px solid rgba(38,38,38,.2); border-radius: 12px; color: inherit; background: rgba(255,255,255,.75); }
/* The action band: a quiet footer for the buttons */
.actions { position: relative; display: flex; flex-flow: row-reverse wrap; justify-content: flex-start; align-items: center; gap: 12px; margin: 26px -28px -28px; padding: 22px 28px;
  background: transparent; border-top: 1px solid rgba(38,38,38,.08); }
.hint { margin-right: auto; font-size: 12px; line-height: 16px; color: #6b7280; }
.hint kbd { font: inherit; font-weight: 700; border: 1px solid #d1d5db; border-radius: 6px; padding: 1px 6px; background: rgba(255,255,255,.7); }
@media (max-width: 480px) { .hint { display: none; } }
.chip, .note { position: absolute; left: 50%; bottom: 96px; transform: translateX(-50%); display: flex; align-items: center; gap: 12px;
  max-width: min(480px, calc(100vw - 32px)); background: #0e141c; color: #eaf0f7; font-size: 14px; line-height: 21px;
  padding: 12px 20px 12px 14px; border: 1px solid #e5e7eb; border-radius: 16px; box-shadow: 0 10px 30px rgba(38,38,38,.16); }
.chip .sentinel, .note .sentinel { width: 30px; }
.banner { position: absolute; top: 0; left: 0; right: 0; background: #0e141c; color: #eaf0f7; border-bottom: 2px solid #22c5e8;
  padding: 14px 20px; font-size: 14px; display: flex; gap: 14px; align-items: center; justify-content: center; flex-wrap: wrap; }
.banner button { min-height: 40px; }
textarea:focus-visible, a:focus-visible { outline: 2px solid #67dbf5; outline-offset: 2px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
@media all {
  .chip, .note { background: #0e141c; color: #eaf0f7; border-color: #2f3a4a; }
  .card { color: #eaf0f7; border-color: rgba(255,255,255,.14); }
  .card { background: linear-gradient(165deg, color-mix(in srgb, var(--dbg) 70%, #0e141c), color-mix(in srgb, var(--dbg) 30%, #080c11)); }
  .card::before { background: var(--dsolid); }
  h2 { color: #eaf0f7; }
  .chipo { color: var(--dfg); }
  p, label { color: #b9c4d2; }
  .found li { background: rgba(255,255,255,.07); border-color: rgba(255,255,255,.14); color: #eaf0f7; }
  .found li::before { background: var(--dsolid); }
  .rib1 { stroke: var(--dsolid); opacity: .3; } .rib2 { opacity: .3; } .rib3 { opacity: .2; stroke: #1e8ca8; }
  .tip { background: rgba(255,255,255,.06); color: #b9c4d2; }
  .actions { border-top-color: rgba(255,255,255,.1); }
  .hint { color: #9eabbc; } .hint kbd { background: rgba(255,255,255,.08); border-color: #2f3a4a; }
  code { background: #080c11; border-color: #2f3a4a; color: #eaf0f7; }
  textarea { background: rgba(255,255,255,.08); color: #eaf0f7; border-color: rgba(255,255,255,.2); }
  .banner { background: #0e141c; color: #eaf0f7; border-bottom-color: #22c5e8; }
}
${TEXTURE_CSS}
`;

/** The five outcome colours from the Sentry kit (light and dark), the icon, and the word shown beside it. */
const lucideEl = (node: IconNode, size = 14): SVGElement =>
  createElement(node, { width: size, height: size, "stroke-width": 2.25, "aria-hidden": "true" });

const ACCENT: Record<
  Action,
  {
    bg: string;
    fg: string;
    solid: string;
    dbg: string;
    dfg: string;
    dsolid: string;
    icon: IconNode;
    word: string;
  }
> = {
  allow: {
    bg: "#e5f6e3",
    fg: "#245420",
    solid: "#30752a",
    dbg: "#0f2a1a",
    dfg: "#8fe3a0",
    dsolid: "#34c759",
    icon: Check,
    word: "Allowed",
  },
  mask: {
    bg: "#f4ecff",
    fg: "#553674",
    solid: "#764aa2",
    dbg: "#24163a",
    dfg: "#d1b3ff",
    dsolid: "#9b6bea",
    icon: EyeOff,
    word: "Masked",
  },
  warn: {
    bg: "#f9efda",
    fg: "#704500",
    solid: "#915b00",
    dbg: "#2e2208",
    dfg: "#f5c56b",
    dsolid: "#e0a020",
    icon: TriangleAlert,
    word: "Warned",
  },
  local: {
    bg: "#e5f2ff",
    fg: "#154a7a",
    solid: "#1666aa",
    dbg: "#0e2438",
    dfg: "#8fc8ff",
    dsolid: "#3b8eea",
    icon: House,
    word: "Answered locally",
  },
  block: {
    bg: "#ffebe9",
    fg: "#7e2122",
    solid: "#b02a2d",
    dbg: "#331216",
    dfg: "#ffa3a3",
    dsolid: "#ef5b5b",
    icon: Ban,
    word: "Blocked",
  },
};

/** An icon beside each card button, by its id. */
const BUTTON_ICON: Record<string, IconNode> = {
  edit: Pencil,
  rewrite: ShieldCheck,
  send: SendHorizontal,
};

/** Three wavy ribbons; each path repeats every 600 units, so sliding the svg by half its width loops seamlessly. */
const WAVE = "M0 60 C100 0 200 0 300 60 S500 120 600 60 S800 0 900 60 S1100 120 1200 60";
const RIBBONS = ["rib1", "rib2", "rib3"]
  .map(
    (c) =>
      `<svg class="rib ${c}" viewBox="0 0 1200 120" preserveAspectRatio="none"><path d="${WAVE}"/></svg>`,
  )
  .join("");

/** The sentinel, inline so a site's content security policy cannot block it. */
const SENTINEL = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 74" role="img" aria-hidden="true" focusable="false"><path d="M32 4 L58 14 V36 C58 52 46 63 32 69 C18 63 6 52 6 36 V14 Z" fill="#22c5e8"/><path d="M32 22 C41 22 47 30 47 36 C47 42 41 50 32 50 C23 50 17 42 17 36 C17 30 23 22 32 22 Z" fill="none" stroke="#04141a" stroke-width="3.5"/><circle class="sentinel-eye" cx="32" cy="36" r="6" fill="#04141a"/></svg>`;

function sentinelEl(): HTMLElement {
  const el = document.createElement("span");
  el.className = "sentinel";
  el.innerHTML = SENTINEL;
  return el;
}

const FONT_FILES: [family: string, weight: string, path: string][] = [
  ["Poppins", "400", "fonts/poppins-400.woff2"],
  ["Poppins", "500", "fonts/poppins-500.woff2"],
  ["Poppins", "600", "fonts/poppins-600.woff2"],
  ["Poppins", "700", "fonts/poppins-700.woff2"],
  ["Space Grotesk", "600", "fonts/space-grotesk-600.woff2"],
];
let fontsRequested = false;

/**
 * Registers Poppins and Space Grotesk for the overlay. The font bytes are read by the extension
 * and handed to FontFace directly, so a site's content security policy (font-src) cannot block them,
 * which a <style> with a chrome-extension:// url would be on sites like ChatGPT.
 */
function loadFonts() {
  if (fontsRequested || typeof chrome === "undefined" || !chrome.runtime?.getURL) return;
  fontsRequested = true;
  for (const [family, weight, path] of FONT_FILES) {
    void (async () => {
      try {
        const res = await fetch(chrome.runtime.getURL(path as never));
        const face = new FontFace(family, await res.arrayBuffer(), { weight });
        document.fonts.add(await face.load());
      } catch {
        /* the system font stack takes over */
      }
    })();
  }
}

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
    loadFonts();
    this.host = document.createElement("hive-overlay");
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
    chip.append(sentinelEl(), document.createTextNode(text));
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
    el.append(sentinelEl(), document.createTextNode(text));
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
    this.layer.querySelector(".cardwrap")?.remove();
    this.lastFocus = document.activeElement;
    const a = ACCENT[opts.action];
    const el = document.createElement("div");
    el.className = "card";
    el.dataset.action = opts.action;
    el.setAttribute("role", "alertdialog");
    el.setAttribute("aria-modal", "true");
    el.setAttribute("aria-labelledby", "hive-title");
    el.setAttribute("aria-describedby", "hive-desc hive-tip");

    // Header band in the outcome colour: the sentinel, the verdict chip, then the headline in its voice.
    const head = document.createElement("div");
    head.className = "head";
    const text = document.createElement("div");
    text.className = "head-text";
    const chipo = document.createElement("span");
    chipo.className = "chipo";
    const icon = document.createElement("i");
    icon.setAttribute("aria-hidden", "true");
    icon.append(lucideEl(a.icon, 14));
    chipo.append(icon, document.createTextNode(a.word));
    const h2 = document.createElement("h2");
    h2.id = "hive-title";
    h2.textContent = opts.title;
    text.append(h2);
    head.append(sentinelEl(), text, chipo);
    for (const [k, v] of Object.entries({
      "--bg": a.bg,
      "--fg": a.fg,
      "--solid": a.solid,
      "--dbg": a.dbg,
      "--dfg": a.dfg,
      "--dsolid": a.dsolid,
    }))
      el.style.setProperty(k, v);

    const main = document.createElement("div");
    main.className = "main";
    const desc = document.createElement("div");
    desc.id = "hive-desc";
    const [first, ...rest] = opts.reasons;
    if (first) {
      const p = document.createElement("p");
      p.textContent = first;
      desc.append(p);
    }
    main.append(desc);
    if (opts.details?.length) {
      const ul = document.createElement("ul");
      ul.className = "found";
      for (const d of opts.details) {
        const li = document.createElement("li");
        li.textContent = d;
        ul.append(li);
      }
      main.append(ul);
    }
    if (opts.preview) {
      const lab = document.createElement("label");
      lab.textContent = opts.preview.label;
      const code = document.createElement("code");
      code.textContent = opts.preview.text;
      main.append(lab, code);
    }
    if (rest.length) {
      const tip = document.createElement("p");
      tip.id = "hive-tip";
      tip.className = "tip";
      tip.textContent = rest.join(" ");
      main.append(tip);
    }
    const rib = document.createElement("div");
    rib.className = "ribbons";
    rib.setAttribute("aria-hidden", "true");
    rib.innerHTML = RIBBONS;
    el.append(rib, head, main);
    let reasonBox: HTMLTextAreaElement | null = null;
    if (opts.askReason) {
      const lab = document.createElement("label");
      lab.htmlFor = "hive-reason";
      lab.textContent = "Why do you need to send this? (saved with the log)";
      reasonBox = document.createElement("textarea");
      reasonBox.id = "hive-reason";
      main.append(lab, reasonBox);
    }
    const actions = document.createElement("div");
    actions.className = "actions";
    const hint = document.createElement("span");
    hint.className = "hint";
    hint.innerHTML = "<kbd>Esc</kbd> to edit";
    main.append(actions);
    const wrap = document.createElement("div");
    wrap.className = "cardwrap";
    const patrol = document.createElement("div");
    patrol.className = "patrol";
    patrol.setAttribute("aria-hidden", "true");
    const psentinel = document.createElement("div");
    psentinel.className = "psentinel";
    const pin = document.createElement("span");
    pin.className = "sentinel";
    pin.innerHTML = SENTINEL;
    psentinel.append(pin);
    patrol.append(psentinel);
    wrap.append(el, patrol);
    this.layer.append(wrap);
    this.announce(`${opts.title}. ${opts.reasons.join(" ")}`);

    return new Promise<CardChoice>((resolve) => {
      const done = (id: string) => {
        wrap.remove();
        document.removeEventListener("keydown", onKey, true);
        if (this.lastFocus instanceof HTMLElement) this.lastFocus.focus();
        resolve({ id, reason: reasonBox?.value.trim() ?? "" });
      };
      const rank = (k?: string) => (k === "primary" ? 0 : k === "danger" ? 2 : 1);
      const ordered = [...opts.buttons].sort((x, y) => rank(x.kind) - rank(y.kind));
      for (const b of ordered) {
        const btn = document.createElement("button");
        btn.type = "button";
        const bi = BUTTON_ICON[b.id];
        if (bi) btn.append(lucideEl(bi, 16));
        btn.append(document.createTextNode(b.label));
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
      actions.append(hint);
      document.addEventListener("keydown", onKey, true);
      (el.querySelector<HTMLElement>("button.primary") ?? focusables()[0])?.focus();
    });
  }
}
