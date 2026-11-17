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
  /** Sideways sway in px across the path, strongest mid-flight. A bee does not fly in a line. */
  sway?: number;
}

export const STEPS = 60;
const START_SCALE = 0.6;
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
  // A wide swoop: the bee first lifts and swings back, then sweeps across and comes in from below.
  const back = to.x >= from.x ? -1 : 1;
  const p1 = inside({ x: from.x + back * 130, y: from.y + (arc === "up" ? -190 : 190) });
  const p2 = inside({ x: to.x - Math.sign(to.x - from.x || 1) * 340, y: to.y + 260 });
  const amp = opts.sway ?? 64;
  const points: Point[] = [];
  for (let i = 0; i <= STEPS; i++) {
    const t = i / STEPS;
    if (i === 0) {
      points.push({ ...from });
      continue;
    }
    if (i === STEPS) {
      points.push({ ...to });
      continue;
    }
    const x = bezier(from.x, p1.x, p2.x, to.x, t);
    const y = bezier(from.y, p1.y, p2.y, to.y, t);
    // Offset sideways to the path, fading in and out so the ends stay exact.
    const dx = bezier(from.x, p1.x, p2.x, to.x, t + 0.001) - x;
    const dy = bezier(from.y, p1.y, p2.y, to.y, t + 0.001) - y;
    const len = Math.hypot(dx, dy) || 1;
    const wave = amp * Math.sin(Math.PI * t) * Math.sin(t * Math.PI * 2 * 2.5);
    points.push({ x: x + (-dy / len) * wave, y: y + (dx / len) * wave });
  }
  return points;
}

export function buildFrames(opts: FlightOptions): Keyframe[] {
  const size = opts.size ?? 56;
  const shrinkTo = opts.shrinkTo ?? 1;
  const points = samplePath(opts);
  // The bee faces the way it travels (the artwork faces left), and tips its nose up as it climbs.
  const flip = opts.to.x > opts.from.x;
  return points.map((p, i) => {
    const t = i / STEPS;
    let scale = START_SCALE + (1 - START_SCALE) * Math.min(1, t * 1.6);
    let opacity = i === 0 ? 0 : 1;
    if (t > TAIL) {
      const k = (t - TAIL) / (1 - TAIL);
      scale = 1 + (shrinkTo - 1) * k;
      if (opts.fadeOutAtEnd) opacity = 1 - k;
    }
    const prev = points[Math.max(0, i - 1)] ?? p;
    const next = points[Math.min(STEPS, i + 1)] ?? p;
    const climb = (Math.atan2(prev.y - next.y, Math.abs(next.x - prev.x) || 1) * 180) / Math.PI;
    const tilt = Math.max(-28, Math.min(28, climb * 0.4)) + Math.sin(t * Math.PI * 5) * 5;
    return {
      transform: `translate(${p.x - size / 2}px,${p.y - size / 2}px) scale(${flip ? -scale : scale},${scale}) rotate(${tilt}deg)`,
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
    duration: opts.duration ?? 1800,
    easing: "cubic-bezier(.37,0,.25,1)",
    fill: "forwards",
  });
  return anim.finished.then(
    () => undefined,
    () => undefined,
  );
}
