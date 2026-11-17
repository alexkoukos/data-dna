import { createBee, createDrop, setState, type BeeState } from "./bee";
import { canAnimate, flyBee, type Point } from "./flight";

export const BEE_STYLE = `
.bee-wrap { display: block; pointer-events: none; }
.bee-wrap svg { width: 100%; height: 100%; overflow: visible; }
.bee-fly { position: absolute; left: 0; top: 0; will-change: transform; pointer-events: none; }
.bee-fixed { position: absolute; pointer-events: none; transition: opacity .2s ease; }
.bee-drop { position: absolute; left: 62%; top: 70%; width: 18px; height: 18px; pointer-events: none; }
.bee-drop.big { width: 26px; height: 26px; }
.bee-glow { position: absolute; border-radius: 4px; background: rgba(233,165,22,.45);
  box-shadow: 0 0 0 3px rgba(233,165,22,.35); pointer-events: none; animation: glow .3s ease-out forwards; }
@keyframes glow { from { opacity: 1; } to { opacity: 0; } }
.perch { position: absolute; top: -52px; left: 14px; width: 68px; height: 68px; pointer-events: none; }
.bee-wrap.still * { animation: none !important; transition: none !important; }
@media (prefers-reduced-motion: reduce) { .bee-glow { animation: none; opacity: 0; } }
`;

const SIZE = 72;
const sleep = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms));

export interface Perch {
  /** Called when the card closes: the bee rests or hops for a moment, then fades. */
  finish(kind: "rest" | "happy"): void;
  remove(): void;
}

/**
 * Draws the guard bee over the page. There is only ever one bee flying at a time; a new event
 * finishes the current animation quickly and starts the new one. Nothing here can block the page.
 */
export class Mascot {
  private current: { el: HTMLElement; anims: () => Animation[]; cleanup: () => void } | null = null;

  constructor(
    private layer: HTMLElement,
    private announce: (text: string) => void,
    private enabled: () => boolean,
  ) {}

  private begin(): HTMLElement {
    this.endCurrent();
    const el = document.createElement("div");
    el.className = "bee-fly";
    this.layer.append(el);
    return el;
  }

  private endCurrent() {
    const cur = this.current;
    if (!cur) return;
    for (const a of cur.anims()) {
      try {
        a.finish();
      } catch {
        /* an animation that cannot finish is cancelled with its element */
      }
    }
    cur.cleanup();
    this.current = null;
  }

  private track(el: HTMLElement) {
    this.current = {
      el,
      anims: () => el.getAnimations(),
      cleanup: () => el.remove(),
    };
  }

  private done(el: HTMLElement) {
    if (this.current?.el === el) this.current = null;
    el.remove();
  }

  private still(): boolean {
    return !canAnimate(this.enabled());
  }

  /** MASK: the bee picks the secret up where it was and carries it to the toolbar icon. */
  async mask(opts: { from: Point; rects?: DOMRect[]; count: number; onLanded: () => void }) {
    const { from, count } = opts;
    this.announce(`${count} item${count === 1 ? "" : "s"} kept safe`);
    if (this.still()) {
      opts.onLanded();
      return;
    }
    for (const r of opts.rects ?? []) {
      const glow = document.createElement("div");
      glow.className = "bee-glow";
      Object.assign(glow.style, {
        left: `${r.left - 2}px`,
        top: `${r.top - 1}px`,
        width: `${r.width + 4}px`,
        height: `${r.height + 2}px`,
      });
      this.layer.append(glow);
      window.setTimeout(() => glow.remove(), 320);
    }
    const el = this.begin();
    const bee = createBee("alert", SIZE);
    el.append(bee);
    el.style.opacity = "0";
    this.track(el);
    const place = (p: Point, scale: number) =>
      `translate(${p.x - SIZE / 2}px,${p.y - SIZE / 2}px) scale(${scale})`;
    // 0 to 150 ms: pop in at the text.
    await el
      .animate(
        [
          { transform: place(from, 0.3), opacity: 0 },
          { transform: place(from, 1), opacity: 1 },
        ],
        { duration: 320, easing: "cubic-bezier(.2,.9,.3,1.2)", fill: "forwards" },
      )
      .finished.catch(() => undefined);
    if (this.current?.el !== el) return; // replaced by a newer bee
    // Then the honey drop lifts and sticks under the bee.
    const drop = createDrop();
    bee.append(drop);
    await drop
      .animate(
        [
          { transform: "translateY(10px)", opacity: 0 },
          { transform: "translateY(0)", opacity: 1 },
        ],
        { duration: 380, easing: "ease-out", fill: "forwards" },
      )
      .finished.catch(() => undefined);
    if (this.current?.el !== el) return;
    setState(bee, "happy");
    // 350 to 1150 ms: along the Bézier to just above the top-right corner, under the toolbar icon.
    await flyBee(el, {
      from,
      to: { x: innerWidth - 36, y: -40 },
      size: SIZE,
      duration: 2000,
      shrinkTo: 0.7,
      fadeOutAtEnd: true,
      arc: "up",
    });
    opts.onLanded();
    this.done(el);
  }

  /** REDIRECT: the whole prompt becomes a drop; the bee carries it to the right edge, towards the side panel. */
  async redirect(from: Point) {
    if (this.still()) return;
    const el = this.begin();
    const bee = createBee("happy", SIZE);
    bee.append(createDrop(true));
    el.append(bee);
    this.track(el);
    await flyBee(el, {
      from,
      to: { x: innerWidth - 20, y: innerHeight / 2 },
      size: SIZE,
      duration: 1600,
      shrinkTo: 0.75,
      fadeOutAtEnd: true,
      arc: "up",
    });
    this.done(el);
  }

  /** A bee sitting on a card's top-left corner. WARN flies it in from the corner; BLOCK pops it in at the send button. */
  perch(card: HTMLElement, mode: "warn" | "block", sendRect?: DOMRect | null): Perch {
    this.endCurrent();
    const perched = createBee("alert", 68);
    perched.classList.add("perch");
    card.append(perched);
    const still = this.still();
    if (still) {
      setState(perched, "idle");
      perched.classList.add("still");
    } else {
      perched.style.visibility = "hidden";
      void this.arrive(perched, mode, sendRect);
    }
    let removed = false;
    const remove = () => {
      removed = true;
      perched.remove();
    };
    return {
      remove,
      finish: (kind) => {
        if (removed) return;
        if (this.still() || !perched.isConnected) return remove();
        // The card is about to go away, so the bee steps off it first.
        const r = perched.getBoundingClientRect();
        const el = document.createElement("div");
        el.className = "bee-fixed";
        Object.assign(el.style, { left: `${r.left}px`, top: `${r.top}px` });
        const bee = createBee(kind, 68);
        el.append(bee);
        this.layer.append(el);
        remove();
        window.setTimeout(() => (el.style.opacity = "0"), 600);
        window.setTimeout(() => el.remove(), 850);
      },
    };
  }

  private async arrive(perched: HTMLElement, mode: "warn" | "block", sendRect?: DOMRect | null) {
    // Wait a frame so the card has its final position.
    await new Promise<void>((r) => requestAnimationFrame(() => r()));
    if (!perched.isConnected) return;
    const target = perched.getBoundingClientRect();
    const to = { x: target.left + target.width / 2, y: target.top + target.height / 2 };
    const el = this.begin();
    const bee = createBee("alert", SIZE);
    el.append(bee);
    this.track(el);
    if (mode === "warn") {
      // WARN: the bee comes to ask, from the top-right corner to the card.
      await flyBee(el, {
        from: { x: innerWidth - 36, y: -40 },
        to,
        size: SIZE,
        duration: 1700,
        arc: "down",
      });
    } else if (sendRect) {
      // BLOCK: no flight. The guard stands in front of the send button, shaking, then settles on the card.
      const at = { x: sendRect.left + sendRect.width / 2, y: sendRect.top + sendRect.height / 2 };
      el.style.transform = `translate(${at.x - SIZE / 2}px,${at.y - SIZE / 2}px)`;
      await el
        .animate(
          [
            {
              transform: `translate(${at.x - SIZE / 2}px,${at.y - SIZE / 2}px) scale(.3)`,
              opacity: 0,
            },
            {
              transform: `translate(${at.x - SIZE / 2}px,${at.y - SIZE / 2}px) scale(1)`,
              opacity: 1,
            },
          ],
          { duration: 250, fill: "forwards" },
        )
        .finished.catch(() => undefined);
      await sleep(900);
    }
    this.done(el);
    if (perched.isConnected) {
      perched.style.visibility = "visible";
      setState(perched, "idle");
    }
  }

  /** A resting bee for the "tool not approved" banner. */
  restingBee(size = 28): HTMLElement {
    const bee = createBee("rest", size);
    if (this.still()) bee.classList.add("still");
    return bee;
  }

  clear() {
    this.endCurrent();
  }
}

export type { BeeState };
