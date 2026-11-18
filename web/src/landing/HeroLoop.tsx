import { useEffect, useReducer, useRef, useState } from "react";
import { Laptop } from "./Laptop";
import { PHASE, PHASES, SCENE_COUNT, initialLoop, loopReducer } from "./loop";
import { Screen } from "./Screen";
import { SCENES } from "./scenes";

function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}

/** True while the element is on screen. */
function useInView(ref: React.RefObject<Element | null>) {
  const [inView, setInView] = useState(true);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), {
      threshold: 0.2,
    });
    io.observe(el);
    return () => io.disconnect();
  }, [ref]);
  return inView;
}

function usePageVisible() {
  const [visible, setVisible] = useState(() => typeof document === "undefined" || !document.hidden);
  useEffect(() => {
    const on = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", on);
    return () => document.removeEventListener("visibilitychange", on);
  }, []);
  return visible;
}

export function HeroLoop() {
  const reduced = useReducedMotion();
  const rootRef = useRef<HTMLDivElement>(null);
  const inView = useInView(rootRef);
  const pageVisible = usePageVisible();
  const [wantsPlay, setWantsPlay] = useState(true);
  const [state, dispatch] = useReducer(loopReducer, initialLoop);

  const playing = !reduced && wantsPlay && inView && pageVisible;
  // Reduced motion: show each scene as a finished frame (the bee card is up) and let people step through.
  const phase = reduced ? PHASE.card : state.phase;

  useEffect(() => {
    if (!playing) return;
    const id = window.setTimeout(() => dispatch({ type: "tick" }), PHASES[state.phase].ms);
    return () => window.clearTimeout(id);
  }, [playing, state.scene, state.phase]);

  const scene = SCENES[state.scene];

  return (
    <div
      ref={rootRef}
      className="hero-loop"
      data-testid="hero-loop"
      data-scene={state.scene}
      data-mode={reduced ? "static" : "loop"}
      data-playing={playing}
    >
      <Laptop>
        <Screen scene={state.scene} phase={phase} />
      </Laptop>

      <p className="loop-caption" aria-live="polite" data-testid="loop-caption">
        <span className="loop-step">
          {state.scene + 1} / {SCENE_COUNT}
        </span>
        {scene.caption}
      </p>
      <p className="sr-only">{scene.demoNote}</p>

      <div className="loop-controls">
        {reduced ? null : (
          <button
            type="button"
            className="btn btn-quiet"
            aria-pressed={!wantsPlay}
            onClick={() => setWantsPlay((v) => !v)}
          >
            {wantsPlay ? "Pause" : "Play"}
          </button>
        )}
        <div className="loop-dots" role="group" aria-label="Choose a scene">
          {SCENES.map((s, i) => (
            <button
              key={s.id}
              type="button"
              className="dot"
              aria-label={`Scene ${i + 1}: ${s.caption}`}
              aria-current={i === state.scene ? "true" : undefined}
              onClick={() => dispatch({ type: "goto", scene: i })}
            >
              <span />
            </button>
          ))}
        </div>
        {reduced ? (
          <button
            type="button"
            className="btn btn-quiet"
            onClick={() => dispatch({ type: "next" })}
          >
            Next
          </button>
        ) : null}
      </div>
    </div>
  );
}
