/**
 * Where on the page is the text the engine caught? The bee starts exactly there.
 * Everything is best effort: when the position cannot be found the caller falls back to the composer.
 */
import type { Point } from "./flight";

export interface Span {
  start: number;
  end: number;
  value?: string;
}

/** Pure: which text node holds a character offset, and where inside it. */
export function locate(lengths: number[], offset: number): { node: number; offset: number } | null {
  let rest = offset;
  for (let i = 0; i < lengths.length; i++) {
    const len = lengths[i] ?? 0;
    if (rest <= len) return { node: i, offset: rest };
    rest -= len;
  }
  return null;
}

/**
 * Pure: the offset of a finding inside the concatenated text nodes. An editor's innerText adds
 * line breaks that the text nodes do not have, so the value is searched for first and the
 * original offset is only a fallback.
 */
export function offsetIn(joined: string, span: Span): number | null {
  if (span.value) {
    const i = joined.indexOf(span.value);
    if (i >= 0) return i;
  }
  return span.end <= joined.length ? span.start : null;
}

const MIRROR_PROPS = [
  "boxSizing",
  "width",
  "height",
  "overflowX",
  "overflowY",
  "borderTopWidth",
  "borderRightWidth",
  "borderBottomWidth",
  "borderLeftWidth",
  "borderStyle",
  "paddingTop",
  "paddingRight",
  "paddingBottom",
  "paddingLeft",
  "fontStyle",
  "fontVariant",
  "fontWeight",
  "fontStretch",
  "fontSize",
  "fontFamily",
  "lineHeight",
  "letterSpacing",
  "textTransform",
  "textIndent",
  "textAlign",
  "tabSize",
] as const;

function textareaRect(el: HTMLTextAreaElement | HTMLInputElement, span: Span): DOMRect | null {
  const value = el.value;
  if (span.end > value.length) return null;
  const mirror = document.createElement("div");
  const cs = getComputedStyle(el);
  for (const p of MIRROR_PROPS) mirror.style[p] = cs[p];
  Object.assign(mirror.style, {
    position: "fixed",
    left: "0",
    top: "0",
    visibility: "hidden",
    whiteSpace: el instanceof HTMLTextAreaElement ? "pre-wrap" : "pre",
    overflowWrap: "break-word",
    pointerEvents: "none",
  });
  const mark = document.createElement("span");
  mark.textContent = value.slice(span.start, span.end) || "​";
  mirror.append(document.createTextNode(value.slice(0, span.start)), mark);
  mirror.append(document.createTextNode(value.slice(span.end)));
  document.body.append(mirror);
  try {
    const m = mirror.getBoundingClientRect();
    const r = mark.getBoundingClientRect();
    const box = el.getBoundingClientRect();
    return new DOMRect(
      box.left + (r.left - m.left) - el.scrollLeft,
      box.top + (r.top - m.top) - el.scrollTop,
      r.width,
      r.height,
    );
  } finally {
    mirror.remove();
  }
}

function editableRect(el: HTMLElement, span: Span): DOMRect | null {
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  for (let n = walker.nextNode(); n; n = walker.nextNode()) nodes.push(n as Text);
  const joined = nodes.map((n) => n.data).join("");
  const start = offsetIn(joined, span);
  if (start === null) return null;
  const length =
    span.value && joined.indexOf(span.value) >= 0 ? span.value.length : span.end - span.start;
  const lengths = nodes.map((n) => n.data.length);
  const a = locate(lengths, start);
  const b = locate(lengths, start + length);
  const na = a && nodes[a.node];
  const nb = b && nodes[b.node];
  if (!a || !b || !na || !nb) return null;
  const range = document.createRange();
  range.setStart(na, a.offset);
  range.setEnd(nb, b.offset);
  const rect = range.getClientRects()[0];
  return rect ? new DOMRect(rect.left, rect.top, rect.width, rect.height) : null;
}

/** The on-screen rectangle of a finding in a composer, or null when it cannot be found. */
export function findingRect(composer: HTMLElement, finding: Span): DOMRect | null {
  try {
    if (composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement) {
      return textareaRect(composer, finding);
    }
    return editableRect(composer, finding);
  } catch {
    return null;
  }
}

/** Centre of the finding, or the left side of the composer, vertically centred. */
export function anchorPoint(composer: HTMLElement, finding: Span | undefined): Point {
  const rect = finding ? findingRect(composer, finding) : null;
  if (rect && rect.width + rect.height > 0) {
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  }
  const box = composer.getBoundingClientRect();
  return { x: box.left + 24, y: box.top + box.height / 2 };
}
