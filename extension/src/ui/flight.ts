/**
 * The bee's flight along a cubic Bézier. The animation is decoration on top of a decision that is
 * already applied, so nothing here is ever awaited before the decision takes effect.
 */
export interface Point {
  x: number;
  y: number;
}

export interface FlightOptions {
  from: Point;
  to: Point;
  /** Width and height of the bee in px. */
  size?: number;
  duration?: number;
  /** Scale at the end of the path. */
  shrinkTo?: number;
  fadeOutAtEnd?: boolean;
  /** Which way the path bows first. */
  arc?: "up" | "down";
  viewport?: { w: number; h: number };
}

export const STEPS = 40;
const START_SCALE = 0.35;
const TAIL = 0.85;

export function bezier(p0: number, p1: number, p2: number, p3: number, t: number): number {
  const u = 1 - t;
  return u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3;
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** The 41 points of the path, from `from` to `to` exactly. Control points stay inside the viewport. */
export function samplePath(opts: FlightOptions): Point[] {
  const { from, to, arc = "up", viewport } = opts;
  const w = viewport?.w ?? (typeof innerWidth === "number" ? innerWidth : 1280);
  const h = viewport?.h ?? (typeof innerHeight === "number" ? innerHeight : 800);
  const inside = (p: Point): Point => ({ x: clamp(p.x, 0, w), y: clamp(p.y, 0, h) });
  const p1 = inside({ x: from.x - 40, y: from.y + (arc === "up" ? -160 : 160) });
  const p2 = inside({ x: to.x - 220, y: to.y + 140 });
  const points: Point[] = [];
  for (let i = 0; i <= STEPS; i++) {
    const t = i / STEPS;
    points.push(
      i === 0
        ? { ...from }
        : i === STEPS
          ? { ...to }
          : {
              x: bezier(from.x, p1.x, p2.x, to.x, t),
              y: bezier(from.y, p1.y, p2.y, to.y, t),
            },
    );
  }
  return points;
}

export function buildFrames(opts: FlightOptions): Keyframe[] {
  const size = opts.size ?? 56;
  const shrinkTo = opts.shrinkTo ?? 1;
  const points = samplePath(opts);
  return points.map((p, i) => {
    const t = i / STEPS;
    let scale = START_SCALE + (1 - START_SCALE) * Math.min(1, t * 1.6);
    let opacity = i === 0 ? 0 : 1;
    if (t > TAIL) {
      const k = (t - TAIL) / (1 - TAIL);
      scale = 1 + (shrinkTo - 1) * k;
      if (opts.fadeOutAtEnd) opacity = 1 - k;
    }
    const tilt = Math.sin(t * Math.PI * 3) * 8;
    return {
      transform: `translate(${p.x - size / 2}px,${p.y - size / 2}px) scale(${scale}) rotate(${tilt}deg)`,
      opacity,
      offset: t,
    };
  });
}

/** False when the person asked for no motion, turned animations off, or the tab is hidden. */
export function canAnimate(enabled = true): boolean {
  if (!enabled) return false;
  if (typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return false;
  }
  if (typeof document !== "undefined" && document.visibilityState !== "visible") return false;
  return true;
}

/** Flies `el` along the path. Resolves when it lands, or at once when motion is off. */
export function flyBee(
  el: HTMLElement,
  opts: FlightOptions & { enabled?: boolean },
): Promise<void> {
  if (!canAnimate(opts.enabled)) return Promise.resolve();
  const anim = el.animate(buildFrames(opts), {
    duration: opts.duration ?? 800,
    easing: "cubic-bezier(.45,0,.2,1)",
    fill: "forwards",
  });
  return anim.finished.then(
    () => undefined,
    () => undefined,
  );
}
