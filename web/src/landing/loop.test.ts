import { describe, expect, it } from "vitest";
import { LOOP_MS, PHASES, SCENE_COUNT, initialLoop, loopReducer, type LoopState } from "./loop";
import { SCENES } from "./scenes";

describe("hero loop state machine", () => {
  it("takes about 24 seconds for four scenes", () => {
    expect(SCENE_COUNT).toBe(4);
    expect(SCENES).toHaveLength(SCENE_COUNT);
    expect(LOOP_MS).toBeGreaterThanOrEqual(22_000);
    expect(LOOP_MS).toBeLessThanOrEqual(26_000);
  });

  it("walks every phase of a scene, then moves to the next scene", () => {
    let s: LoopState = initialLoop;
    for (let i = 0; i < PHASES.length - 1; i++) s = loopReducer(s, { type: "tick" });
    expect(s).toEqual({ scene: 0, phase: PHASES.length - 1 });
    s = loopReducer(s, { type: "tick" });
    expect(s).toEqual({ scene: 1, phase: 0 });
  });

  it("visits all four scenes and wraps back to the first", () => {
    let s: LoopState = initialLoop;
    const seen = new Set<number>();
    for (let i = 0; i < PHASES.length * SCENE_COUNT; i++) {
      seen.add(s.scene);
      s = loopReducer(s, { type: "tick" });
    }
    expect([...seen]).toEqual([0, 1, 2, 3]);
    expect(s).toEqual(initialLoop);
  });

  it("goes to a chosen scene and steps with next and prev", () => {
    expect(loopReducer(initialLoop, { type: "goto", scene: 2 })).toEqual({ scene: 2, phase: 0 });
    expect(loopReducer({ scene: 3, phase: 4 }, { type: "next" })).toEqual({ scene: 0, phase: 0 });
    expect(loopReducer(initialLoop, { type: "prev" })).toEqual({ scene: 3, phase: 0 });
  });
});

describe("scene data", () => {
  it("keeps real-looking values out of the masked text", () => {
    for (const scene of SCENES) {
      for (const line of scene.paste)
        for (const seg of line)
          if (typeof seg !== "string") expect(seg.pill).toMatch(/^\[[A-Z_]+_\d\]$/);
    }
  });

  it("gives every block a safe way forward", () => {
    for (const scene of SCENES) {
      expect(scene.card.primary.length).toBeGreaterThan(0);
      expect(scene.card.tip.length).toBeGreaterThan(0);
    }
  });
});
