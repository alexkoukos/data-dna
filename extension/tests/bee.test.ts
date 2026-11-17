import { afterEach, describe, expect, it, vi } from "vitest";
import beeSvg from "../assets/bee.svg?raw";
import { locate, offsetIn } from "../src/ui/anchor";
import { uniqueBeeSvg } from "../src/ui/bee";
import { buildFrames, canAnimate, flyBee, samplePath, STEPS } from "../src/ui/flight";

const viewport = { w: 1280, h: 800 };
const from = { x: 300, y: 600 };
const exit = { x: 1244, y: -40 };

afterEach(() => vi.unstubAllGlobals());

describe("flight path", () => {
  it("samples a path of points that start at `from` and end exactly at `to`", () => {
    const pts = samplePath({ from, to: exit, viewport });
    expect(pts).toHaveLength(STEPS + 1);
    expect(pts[0]).toEqual(from);
    expect(pts[STEPS]).toEqual(exit);
  });

  it("builds one keyframe per point with offsets from 0 to 1", () => {
    const frames = buildFrames({ from, to: exit, size: 56, viewport });
    expect(frames).toHaveLength(STEPS + 1);
    expect(frames[0]?.offset).toBe(0);
    expect(frames[STEPS]?.offset).toBe(1);
    // The element is positioned by its top-left corner, so the centre is `from`.
    expect(frames[0]?.transform).toContain(`translate(${from.x - 28}px,${from.y - 28}px)`);
  });

  it("shrinks and fades over the last 15% when asked", () => {
    const frames = buildFrames({ from, to: exit, viewport, shrinkTo: 0.4, fadeOutAtEnd: true });
    const last = frames[STEPS];
    expect(last?.opacity).toBe(0);
    expect(String(last?.transform)).toMatch(/scale\(-?0\.4,0\.4\)/);
    expect(frames[Math.floor(STEPS * 0.8)]?.opacity).toBe(1);
  });

  it("keeps the bee visible at the end when it should land on a card", () => {
    const frames = buildFrames({ from: exit, to: from, viewport, arc: "down" });
    expect(frames[STEPS]?.opacity).toBe(1);
  });
});

describe("trajectory", () => {
  it("is not a straight line: it sways to both sides of the direct route", () => {
    const pts = samplePath({ from, to: exit, viewport });
    const side = (p: { x: number; y: number }) =>
      (exit.x - from.x) * (p.y - from.y) - (exit.y - from.y) * (p.x - from.x);
    expect(pts.some((p) => side(p) > 1500)).toBe(true);
    expect(pts.some((p) => side(p) < -1500)).toBe(true);
  });

  it("faces the way it travels: flipped when flying right, not when flying left", () => {
    const right = buildFrames({ from, to: exit, viewport });
    const left = buildFrames({ from: exit, to: from, viewport });
    expect(String(right[10]?.transform)).toMatch(/scale\(-/);
    expect(String(left[10]?.transform)).not.toMatch(/scale\(-/);
  });

  it("tilts the nose by a bounded angle", () => {
    for (const f of buildFrames({ from, to: exit, viewport })) {
      const deg = Number(/rotate\((-?[\d.]+)deg\)/.exec(String(f.transform))?.[1]);
      expect(Math.abs(deg)).toBeLessThanOrEqual(33);
    }
  });
});

describe("reduced motion", () => {
  const visible = { visibilityState: "visible" };

  it("allows motion by default and refuses it when switched off", () => {
    vi.stubGlobal("document", visible);
    vi.stubGlobal("matchMedia", () => ({ matches: false }));
    expect(canAnimate(true)).toBe(true);
    expect(canAnimate(false)).toBe(false);
  });

  it("refuses motion when the person prefers reduced motion, and returns at once", async () => {
    vi.stubGlobal("document", visible);
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    expect(canAnimate(true)).toBe(false);
    const el = {
      animate: () => {
        throw new Error("must not animate");
      },
    } as unknown as HTMLElement;
    await expect(flyBee(el, { from, to: exit, viewport })).resolves.toBeUndefined();
  });

  it("refuses motion in a hidden tab", () => {
    vi.stubGlobal("document", { visibilityState: "hidden" });
    vi.stubGlobal("matchMedia", () => ({ matches: false }));
    expect(canAnimate(true)).toBe(false);
  });
});

describe("unique clipPath ids", () => {
  it("gives three bees three different ids, and each stripe group points at its own", () => {
    const bees = [0, 1, 2].map((n) => uniqueBeeSvg(beeSvg, n));
    const ids = bees.map((b) => /id="(bee-body-clip-\d+)"/.exec(b)?.[1]);
    expect(new Set(ids).size).toBe(3);
    bees.forEach((b, i) => {
      expect(b).toContain(`clip-path="url(#bee-body-clip-${i})"`);
      expect(b).not.toContain('id="bee-body-clip"');
      expect(b).not.toContain("url(#bee-body-clip)");
    });
  });
});

describe("finding offsets", () => {
  it("finds the text node and the offset inside it", () => {
    expect(locate([5, 10, 3], 0)).toEqual({ node: 0, offset: 0 });
    expect(locate([5, 10, 3], 5)).toEqual({ node: 0, offset: 5 });
    expect(locate([5, 10, 3], 7)).toEqual({ node: 1, offset: 2 });
    expect(locate([5, 10, 3], 18)).toEqual({ node: 2, offset: 3 });
    expect(locate([5, 10, 3], 19)).toBeNull();
  });

  it("searches for the value first, because innerText adds line breaks the text nodes lack", () => {
    // The engine saw "a\n\nGR16..." (offset 3); the text nodes hold "aGR16...".
    const joined = "aGR1601101250000000012300695";
    expect(offsetIn(joined, { start: 3, end: 30, value: "GR1601101250000000012300695" })).toBe(1);
  });

  it("falls back to the engine's offset, or gives up when it does not fit", () => {
    expect(offsetIn("hello world", { start: 6, end: 11 })).toBe(6);
    expect(offsetIn("hi", { start: 6, end: 11 })).toBeNull();
  });
});
