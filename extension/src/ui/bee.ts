import beeSvg from "../../assets/bee.svg?raw";

export type BeeState = "idle" | "alert" | "happy" | "rest";

const CLIP_ID = "bee-body-clip";
let counter = 0;

/** Every bee needs its own clipPath id, or the stripes break when two bees exist. */
export function uniqueBeeSvg(svg: string, n: number): string {
  return svg
    .replaceAll(`id="${CLIP_ID}"`, `id="${CLIP_ID}-${n}"`)
    .replaceAll(`url(#${CLIP_ID})`, `url(#${CLIP_ID}-${n})`);
}

export function setState(el: Element, state: BeeState) {
  const svg = el.querySelector("svg") ?? el;
  svg.classList.remove("is-alert", "is-happy", "is-rest");
  if (state !== "idle") svg.classList.add(`is-${state}`);
}

/** A wrapper around one bee. Hidden from assistive technology: it only decorates. */
export function createBee(state: BeeState = "idle", size = 56): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "bee-wrap";
  wrap.setAttribute("aria-hidden", "true");
  wrap.style.width = `${size}px`;
  wrap.style.height = `${size}px`;
  wrap.innerHTML = uniqueBeeSvg(beeSvg, counter++);
  setState(wrap, state);
  return wrap;
}

/** The small amber drop with a lock that the bee carries. */
export function createDrop(big = false): HTMLElement {
  const d = document.createElement("div");
  d.className = big ? "bee-drop big" : "bee-drop";
  d.setAttribute("aria-hidden", "true");
  d.innerHTML =
    '<svg viewBox="0 0 16 16" width="100%" height="100%"><circle cx="8" cy="8" r="7.5" fill="#E9A516" stroke="#141414" stroke-width="1.2"/>' +
    '<rect x="5" y="7.4" width="6" height="4.4" rx="1" fill="#141414"/>' +
    '<path d="M6.2 7.4V6.2a1.8 1.8 0 0 1 3.6 0v1.2" fill="none" stroke="#141414" stroke-width="1.1"/></svg>';
  return d;
}
