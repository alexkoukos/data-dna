import type { Action } from "./detect/policy";

/**
 * Everything the person sees on top of an AI site. It lives in a Shadow DOM so the site's CSS
 * cannot break it and ours cannot leak into the site.
 */
const STYLE = `
:host { all: initial; }
* { box-sizing: border-box; font-family: 'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.layer { position: fixed; inset: 0; pointer-events: none; z-index: 2147483647; }
.card, .chip, .banner, .note { pointer-events: auto; }
.card {
  position: absolute; left: 50%; bottom: 96px; transform: translateX(-50%);
  width: min(460px, calc(100vw - 32px)); background: #fff; color: #262626;
  border: 1px solid #e5e7eb; border-radius: 14px;
  box-shadow: 0 10px 30px rgba(38,38,38,.16);
  padding: 16px 18px 16px; animation: rise .18s ease-out;
}
@keyframes rise { from { opacity: 0; transform: translate(-50%, 10px); } to { opacity: 1; transform: translate(-50%, 0); } }
@media (prefers-reduced-motion: reduce) { .card { animation: none; } }
.top { display: flex; align-items: center; gap: 10px; }
.bee { flex: none; width: 36px; }
.bee svg { display: block; width: 100%; height: auto; }
h2 { margin: 0; font-size: 17px; line-height: 24px; font-weight: 800; }
p { margin: 0 0 6px; font-size: 14px; line-height: 21px; color: #525252; }
.body { margin-top: 8px; }
ul { margin: 6px 0 8px; padding-left: 18px; font-size: 13px; line-height: 20px; color: #525252; }
.meta { display: flex; align-items: center; gap: 10px; margin: 10px 0; }
.chipo { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; line-height: 16px; font-weight: 700;
  color: var(--fg); background: var(--bg); border-radius: 9999px; padding: 3px 10px 3px 8px; }
.chipo i { font-style: normal; font-size: 10px; line-height: 1; }
.tip { margin: 0; padding: 8px 12px; border-radius: 10px; background: #fffbeb; font-size: 13px; line-height: 20px; color: #525252; }
code { font-family: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace; background: #f9fafb; border: 1px solid #e5e7eb;
  border-radius: 6px; padding: 2px 6px; font-size: 12px; color: #262626; display: block; margin: 4px 0 8px; white-space: pre-wrap; }
label { display: block; font-size: 13px; font-weight: 700; margin: 12px 0 4px; color: #262626; }
textarea { width: 100%; min-height: 54px; resize: vertical; font-size: 14px; padding: 8px 10px;
  border: 1px solid #d1d5db; border-radius: 10px; color: inherit; background: #fff; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
button { min-height: 44px; padding: 0 16px; border-radius: 10px; font-size: 14px; font-weight: 700;
  cursor: pointer; border: 1px solid #e5e7eb; background: #fff; color: #262626; }
button:hover { background: #f3f4f6; }
button.primary { background: #f59e0b; border-color: #f59e0b; color: #262626; }
button.primary:hover { background: #e9a516; }
button.danger { background: #fff; border-color: #b02a2d; color: #7e2122; }
button:focus-visible, textarea:focus-visible, a:focus-visible { outline: 2px solid #262626; outline-offset: 2px; box-shadow: 0 0 0 5px #f59e0b; }
.chip, .note { position: absolute; left: 50%; bottom: 96px; transform: translateX(-50%); display: flex; align-items: center; gap: 8px;
  max-width: min(460px, calc(100vw - 32px)); background: #fff; color: #262626; font-size: 13px; line-height: 19px;
  padding: 8px 14px 8px 10px; border: 1px solid #e5e7eb; border-radius: 14px; box-shadow: 0 6px 20px rgba(38,38,38,.14); }
.chip .bee, .note .bee { width: 26px; }
.banner { position: absolute; top: 0; left: 0; right: 0; background: #fffbeb; color: #262626; border-bottom: 2px solid #f59e0b;
  padding: 10px 16px; font-size: 14px; display: flex; gap: 12px; align-items: center; justify-content: center; flex-wrap: wrap; }
.banner button { min-height: 36px; padding: 0 12px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
@media (prefers-color-scheme: dark) {
  .card, .chip, .note { background: #262626; color: #fafaf9; border-color: #404040; }
  p, ul, label, .tip { color: #d4d4d4; } .tip { background: #333; }
  code { background: #1f1f1f; border-color: #404040; color: #fafaf9; }
  textarea, button { background: #2b2b2b; color: #fafaf9; border-color: #404040; }
  button.primary { background: #f59e0b; color: #262626; } button.danger { color: #ff9a92; border-color: #ff9a92; }
  .banner { background: #262626; color: #fafaf9; }
}
`;

/** The five outcome colours from the Hive kit: background, text, and the word shown next to the icon. */
const ACCENT: Record<Action, { bg: string; fg: string; icon: string; word: string }> = {
  allow: { bg: "#e5f6e3", fg: "#245420", icon: "✓", word: "Allowed" },
  mask: { bg: "#f4ecff", fg: "#553674", icon: "◐", word: "Masked" },
  warn: { bg: "#f9efda", fg: "#704500", icon: "▲", word: "Warned" },
  local: { bg: "#e5f2ff", fg: "#154a7a", icon: "⌂", word: "Answered locally" },
  block: { bg: "#ffebe9", fg: "#7e2122", icon: "■", word: "Blocked" },
};

/** The guard bee, inline so a site's content security policy cannot block it. */
const BEE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="641.50 322.75 66.70 50.50" role="img" aria-hidden="true" focusable="false"><path d="M672.00 333.75C672.00 334.34 671.91 334.93 671.74 335.51C671.57 336.09 671.31 336.65 670.97 337.19C670.63 337.74 670.22 338.26 669.72 338.75C669.23 339.24 668.67 339.70 668.05 340.11C667.42 340.53 666.74 340.90 666.00 341.23C665.26 341.56 664.49 341.84 663.67 342.06C662.85 342.29 662.00 342.46 661.13 342.58C660.26 342.69 659.39 342.75 658.50 342.75C657.61 342.75 656.74 342.69 655.87 342.58C655.00 342.46 654.15 342.29 653.33 342.06C652.51 341.84 651.74 341.56 651.00 341.23C650.26 340.90 649.58 340.53 648.95 340.11C648.33 339.70 647.77 339.24 647.28 338.75C646.78 338.26 646.37 337.74 646.03 337.19C645.69 336.65 645.43 336.09 645.26 335.51C645.09 334.93 645.00 334.34 645.00 333.75C645.00 333.16 645.09 332.57 645.26 331.99C645.43 331.41 645.69 330.85 646.03 330.31C646.37 329.76 646.78 329.24 647.28 328.75C647.77 328.26 648.33 327.80 648.95 327.39C649.58 326.97 650.26 326.60 651.00 326.27C651.74 325.94 652.51 325.66 653.33 325.44C654.15 325.21 655.00 325.04 655.87 324.92C656.74 324.81 657.61 324.75 658.50 324.75C659.39 324.75 660.26 324.81 661.13 324.92C662.00 325.04 662.85 325.21 663.67 325.44C664.49 325.66 665.26 325.94 666.00 326.27C666.74 326.60 667.42 326.97 668.05 327.39C668.67 327.80 669.23 328.26 669.72 328.75C670.22 329.24 670.63 329.76 670.97 330.31C671.31 330.85 671.57 331.41 671.74 331.99C671.91 332.57 672.00 333.16 672.00 333.75" fill="#FFFFFF" stroke="#262626" stroke-width="3.00" stroke-linecap="round" stroke-linejoin="round"/><path d="M693.00 333.75C693.00 334.34 692.91 334.93 692.74 335.51C692.57 336.09 692.31 336.65 691.97 337.19C691.63 337.74 691.22 338.26 690.72 338.75C690.23 339.24 689.67 339.70 689.05 340.11C688.42 340.53 687.74 340.90 687.00 341.23C686.26 341.56 685.49 341.84 684.67 342.06C683.85 342.29 683.00 342.46 682.13 342.58C681.26 342.69 680.39 342.75 679.50 342.75C678.61 342.75 677.74 342.69 676.87 342.58C676.00 342.46 675.15 342.29 674.33 342.06C673.51 341.84 672.74 341.56 672.00 341.23C671.26 340.90 670.58 340.53 669.95 340.11C669.33 339.70 668.77 339.24 668.28 338.75C667.78 338.26 667.37 337.74 667.03 337.19C666.69 336.65 666.43 336.09 666.26 335.51C666.09 334.93 666.00 334.34 666.00 333.75C666.00 333.16 666.09 332.57 666.26 331.99C666.43 331.41 666.69 330.85 667.03 330.31C667.37 329.76 667.78 329.24 668.28 328.75C668.77 328.26 669.33 327.80 669.95 327.39C670.58 326.97 671.26 326.60 672.00 326.27C672.74 325.94 673.51 325.66 674.33 325.44C675.15 325.21 676.00 325.04 676.87 324.92C677.74 324.81 678.61 324.75 679.50 324.75C680.39 324.75 681.26 324.81 682.13 324.92C683.00 325.04 683.85 325.21 684.67 325.44C685.49 325.66 686.26 325.94 687.00 326.27C687.74 326.60 688.42 326.97 689.05 327.39C689.67 327.80 690.23 328.26 690.72 328.75C691.22 329.24 691.63 329.76 691.97 330.31C692.31 330.85 692.57 331.41 692.74 331.99C692.91 332.57 693.00 333.16 693.00 333.75" fill="#FFFFFF" stroke="#262626" stroke-width="3.00" stroke-linecap="round" stroke-linejoin="round"/><path d="M691.50 354.75C691.50 355.29 691.46 355.83 691.38 356.37C691.31 356.91 691.19 357.44 691.04 357.97C690.89 358.50 690.69 359.02 690.47 359.54C690.24 360.06 689.97 360.57 689.67 361.06C689.37 361.56 689.04 362.05 688.67 362.53C688.30 363.00 687.89 363.47 687.46 363.92C687.02 364.37 686.55 364.80 686.05 365.22C685.55 365.64 685.03 366.04 684.47 366.42C683.91 366.80 683.33 367.16 682.73 367.50C682.12 367.85 681.49 368.17 680.83 368.47C680.18 368.77 679.51 369.05 678.81 369.30C678.12 369.56 677.41 369.79 676.68 369.99C675.96 370.20 675.22 370.38 674.47 370.54C673.71 370.70 672.95 370.83 672.18 370.93C671.41 371.04 670.63 371.12 669.85 371.17C669.07 371.22 668.29 371.25 667.50 371.25C666.71 371.25 665.93 371.22 665.15 371.17C664.37 371.12 663.59 371.04 662.82 370.93C662.05 370.83 661.29 370.70 660.53 370.54C659.78 370.38 659.04 370.20 658.32 369.99C657.59 369.79 656.88 369.56 656.19 369.30C655.49 369.05 654.82 368.77 654.17 368.47C653.51 368.17 652.88 367.85 652.27 367.50C651.67 367.16 651.09 366.80 650.53 366.42C649.97 366.04 649.45 365.64 648.95 365.22C648.45 364.80 647.98 364.37 647.54 363.92C647.11 363.47 646.70 363.00 646.33 362.53C645.96 362.05 645.63 361.56 645.33 361.06C645.03 360.57 644.76 360.06 644.53 359.54C644.31 359.02 644.11 358.50 643.96 357.97C643.81 357.44 643.69 356.91 643.62 356.37C643.54 355.83 643.50 355.29 643.50 354.75C643.50 354.21 643.54 353.67 643.62 353.13C643.69 352.59 643.81 352.06 643.96 351.53C644.11 351.00 644.31 350.48 644.53 349.96C644.76 349.44 645.03 348.93 645.33 348.44C645.63 347.94 645.96 347.45 646.33 346.97C646.70 346.50 647.11 346.03 647.54 345.58C647.98 345.13 648.45 344.70 648.95 344.28C649.45 343.86 649.97 343.46 650.53 343.08C651.09 342.70 651.67 342.34 652.27 342.00C652.88 341.65 653.51 341.33 654.17 341.03C654.82 340.73 655.49 340.45 656.19 340.20C656.88 339.94 657.59 339.71 658.32 339.51C659.04 339.30 659.78 339.12 660.53 338.96C661.29 338.80 662.05 338.67 662.82 338.57C663.59 338.46 664.37 338.38 665.15 338.33C665.93 338.28 666.71 338.25 667.50 338.25C668.29 338.25 669.07 338.28 669.85 338.33C670.63 338.38 671.41 338.46 672.18 338.57C672.95 338.67 673.71 338.80 674.47 338.96C675.22 339.12 675.96 339.30 676.68 339.51C677.41 339.71 678.12 339.94 678.81 340.20C679.51 340.45 680.18 340.73 680.83 341.03C681.49 341.33 682.12 341.65 682.73 342.00C683.33 342.34 683.91 342.70 684.47 343.08C685.03 343.46 685.55 343.86 686.05 344.28C686.55 344.70 687.02 345.13 687.46 345.58C687.89 346.03 688.30 346.50 688.67 346.97C689.04 347.45 689.37 347.94 689.67 348.44C689.97 348.93 690.24 349.44 690.47 349.96C690.69 350.48 690.89 351.00 691.04 351.53C691.19 352.06 691.31 352.59 691.38 353.13C691.46 353.67 691.50 354.21 691.50 354.75" fill="#F59E0B"/><path d="M661.50 339.75L661.50 369.75M673.50 339.75L673.50 369.75" fill="none" stroke="#262626" stroke-width="6.00" stroke-linecap="round" stroke-linejoin="round"/><path d="M706.20 354.75C706.20 355.42 706.13 356.08 706.00 356.74C705.87 357.40 705.68 358.03 705.42 358.65C705.17 359.27 704.85 359.86 704.48 360.42C704.11 360.97 703.69 361.49 703.21 361.96C702.74 362.44 702.22 362.86 701.67 363.23C701.11 363.60 700.52 363.92 699.90 364.17C699.28 364.43 698.65 364.62 697.99 364.75C697.33 364.88 696.67 364.95 696.00 364.95C695.33 364.95 694.67 364.88 694.01 364.75C693.35 364.62 692.72 364.43 692.10 364.17C691.48 363.92 690.89 363.60 690.33 363.23C689.78 362.86 689.26 362.44 688.79 361.96C688.31 361.49 687.89 360.97 687.52 360.42C687.15 359.86 686.83 359.27 686.58 358.65C686.32 358.03 686.13 357.40 686.00 356.74C685.87 356.08 685.80 355.42 685.80 354.75C685.80 354.08 685.87 353.42 686.00 352.76C686.13 352.10 686.32 351.47 686.58 350.85C686.83 350.23 687.15 349.64 687.52 349.08C687.89 348.53 688.31 348.01 688.79 347.54C689.26 347.06 689.78 346.64 690.33 346.27C690.89 345.90 691.48 345.58 692.10 345.33C692.72 345.07 693.35 344.88 694.01 344.75C694.67 344.62 695.33 344.55 696.00 344.55C696.67 344.55 697.33 344.62 697.99 344.75C698.65 344.88 699.28 345.07 699.90 345.33C700.52 345.58 701.11 345.90 701.67 346.27C702.22 346.64 702.74 347.06 703.21 347.54C703.69 348.01 704.11 348.53 704.48 349.08C704.85 349.64 705.17 350.23 705.42 350.85C705.68 351.47 705.87 352.10 706.00 352.76C706.13 353.42 706.20 354.08 706.20 354.75" fill="#262626"/></svg>`;

function beeEl(): HTMLElement {
  const el = document.createElement("span");
  el.className = "bee";
  el.innerHTML = BEE;
  return el;
}

/** Registers Plus Jakarta Sans on the page (fonts declared inside a shadow root do not load). */
function loadFonts() {
  if (
    document.getElementById("hive-fonts") ||
    typeof chrome === "undefined" ||
    !chrome.runtime?.getURL
  )
    return;
  const css = [400, 500, 700, 800]
    .map(
      (w) =>
        `@font-face{font-family:"Plus Jakarta Sans";font-weight:${w};font-display:swap;src:url("${chrome.runtime.getURL(`fonts/pjs-${w}.woff2` as never)}") format("woff2")}`,
    )
    .join("");
  const style = document.createElement("style");
  style.id = "hive-fonts";
  style.textContent = css;
  document.head.append(style);
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
    chip.append(beeEl(), document.createTextNode(text));
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
    el.append(beeEl(), document.createTextNode(text));
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
    el.setAttribute("role", "alertdialog");
    el.setAttribute("aria-modal", "true");
    el.setAttribute("aria-labelledby", "pyli-title");
    el.setAttribute("aria-describedby", "pyli-desc pyli-tip");

    // The bee speaks first: headline in its voice, then what it did, then the way out.
    const top = document.createElement("div");
    top.className = "top";
    const h2 = document.createElement("h2");
    h2.id = "pyli-title";
    h2.textContent = opts.title;
    top.append(beeEl(), h2);
    const desc = document.createElement("div");
    desc.id = "pyli-desc";
    desc.className = "body";
    const [first, ...rest] = opts.reasons;
    if (first) {
      const p = document.createElement("p");
      p.textContent = first;
      desc.append(p);
    }
    el.append(top, desc);

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
    const meta = document.createElement("div");
    meta.className = "meta";
    const chipo = document.createElement("span");
    chipo.className = "chipo";
    chipo.style.setProperty("--bg", a.bg);
    chipo.style.setProperty("--fg", a.fg);
    const icon = document.createElement("i");
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = a.icon;
    chipo.append(icon, document.createTextNode(a.word));
    meta.append(chipo);
    el.append(meta);
    if (rest.length) {
      const tip = document.createElement("p");
      tip.id = "pyli-tip";
      tip.className = "tip";
      tip.textContent = rest.join(" ");
      el.append(tip);
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
      const rank = (k?: string) => (k === "primary" ? 0 : k === "danger" ? 2 : 1);
      const ordered = [...opts.buttons].sort((x, y) => rank(x.kind) - rank(y.kind));
      for (const b of ordered) {
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
