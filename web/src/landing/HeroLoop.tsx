import { useEffect, useReducer, useRef, useState } from "react";
import { AppWindow } from "./AppWindow";
import { PHASE, PHASES, SCENE_COUNT, initialLoop, loopReducer } from "./loop";
import { TextureButton } from "@/components/ui/texture-button";
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
  const [state, dispatch] = useReducer(loopReducer, initialLoop);

  const playing = !reduced && inView && pageVisible;
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
      <AppWindow>
        <Screen scene={state.scene} phase={phase} />
      </AppWindow>

      {/* Spoken captions for screen readers; the demo itself carries the story visually. */}
      <p className="sr-only" aria-live="polite" data-testid="loop-caption">
        {state.scene + 1} / {SCENE_COUNT} {scene.caption}
      </p>
      <p className="sr-only">{scene.demoNote}</p>

      {reduced ? (
        <div className="loop-controls">
          <TextureButton variant="secondary" onClick={() => dispatch({ type: "next" })}>
            Next
          </TextureButton>
        </div>
      ) : null}
    </div>
  );
}
