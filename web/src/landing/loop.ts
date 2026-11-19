// The hero loop is a tiny state machine: 4 scenes, each walking through the same 6 phases.
// Pure functions only, so the timeline is easy to test and the React side just renders it.

export const PHASES = [
  { id: "idle", ms: 500 },
  { id: "type", ms: 1000 },
  { id: "paste", ms: 900 },
  { id: "sentinel", ms: 1200 },
  { id: "card", ms: 1500 },
  { id: "hold", ms: 900 },
] as const;

export type PhaseId = (typeof PHASES)[number]["id"];

export const PHASE = {
  idle: 0,
  type: 1,
  paste: 2,
  sentinel: 3,
  card: 4,
  hold: 5,
} as const satisfies Record<PhaseId, number>;

/** One full pass over all scenes takes about 24 s. */
export const SCENE_COUNT = 4;
export const LOOP_MS = PHASES.reduce((sum, p) => sum + p.ms, 0) * SCENE_COUNT;

export type LoopState = { scene: number; phase: number };
export type LoopAction =
  | { type: "tick" }
  | { type: "goto"; scene: number; phase?: number }
  | { type: "next" }
  | { type: "prev" };

export const initialLoop: LoopState = { scene: 0, phase: 0 };

const wrap = (n: number) => ((n % SCENE_COUNT) + SCENE_COUNT) % SCENE_COUNT;

export function loopReducer(state: LoopState, action: LoopAction): LoopState {
  switch (action.type) {
    case "tick":
      if (state.phase < PHASES.length - 1) return { scene: state.scene, phase: state.phase + 1 };
      return { scene: wrap(state.scene + 1), phase: 0 };
    case "goto":
      return { scene: wrap(action.scene), phase: action.phase ?? 0 };
    case "next":
      return { scene: wrap(state.scene + 1), phase: 0 };
    case "prev":
      return { scene: wrap(state.scene - 1), phase: 0 };
  }
}
