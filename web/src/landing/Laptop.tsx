import { useEffect, useRef, type ReactNode } from "react";
import { Scaled } from "./Scaled";

// A photo of a real laptop (public/brand/laptop.webp, 1575 x 1330) with the display cut out.
// The screen is drawn behind it and pinned to the four corners of the display with a
// perspective transform, so it sits at the same angle as the lid in the photo.
export const LAPTOP_W = 1575;
export const LAPTOP_H = 1330;
// The browser window is 720 x 450; a 26 px menu bar above it makes 720 x 476.
const CONTENT = { w: 720, h: 476 };
// Display corners in the photo: top-left, top-right, bottom-right, bottom-left.
// matrix3d maps the CONTENT rectangle onto them (solved once, see the note in the PR).
const SCREEN_MATRIX =
  "matrix3d(1.7349502,-0.028563903,0,-2.3821973e-05,0.37655183,1.8600877,0,0.0003978063,0,0,1,0,174,53,0,1)";

// Scroll effect (the ContainerScroll look): the lid starts tipped back and settles flat
// over the first SCROLL_RANGE pixels of scroll. Set straight on the element, no re-render.
const SCROLL_RANGE = 420;

function useTiltOnScroll(ref: React.RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const flat = "perspective(1800px) rotateX(0deg) scale(1)";
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.style.transform = flat;
      return;
    }
    let raf = 0;
    const apply = () => {
      raf = 0;
      const p = Math.min(1, Math.max(0, window.scrollY / SCROLL_RANGE));
      const e = 1 - (1 - p) * (1 - p); // ease out
      el.style.transform = `perspective(1800px) rotateX(${(18 * (1 - e)).toFixed(2)}deg) scale(${(1.06 - 0.06 * e).toFixed(4)})`;
    };
    const on = () => {
      if (!raf) raf = requestAnimationFrame(apply);
    };
    apply();
    window.addEventListener("scroll", on, { passive: true });
    return () => {
      window.removeEventListener("scroll", on);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [ref]);
}

export function Laptop({ children }: { children: ReactNode }) {
  const tiltRef = useRef<HTMLDivElement>(null);
  useTiltOnScroll(tiltRef);
  return (
    <Scaled width={LAPTOP_W} height={LAPTOP_H} max={1} align="right" className="laptop-wrap">
      <div className="laptop" ref={tiltRef}>
        <div className="laptop-glow" aria-hidden="true" />
        <div
          className="laptop-content"
          style={{ width: CONTENT.w, height: CONTENT.h, transform: SCREEN_MATRIX }}
        >
          <div className="menubar" aria-hidden="true">
            <span className="menubar-app">Browser</span>
            <span>File</span>
            <span>Edit</span>
            <span>View</span>
            <span>History</span>
            <span className="menubar-status">
              <svg
                width="16"
                height="12"
                viewBox="0 0 16 12"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <path d="M1.5 4.2a9 9 0 0 1 13 0M3.8 6.8a5.7 5.7 0 0 1 8.4 0M6.2 9.3a2.4 2.4 0 0 1 3.6 0" />
              </svg>
              <svg width="26" height="12" viewBox="0 0 26 12" fill="none">
                <rect
                  x="0.75"
                  y="1.25"
                  width="21"
                  height="9.5"
                  rx="2.5"
                  stroke="currentColor"
                  strokeWidth="1.2"
                />
                <rect x="2.5" y="3" width="14" height="6" rx="1.2" fill="currentColor" />
                <path
                  d="M23.6 4.4v3.2"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                />
              </svg>
              <span>Tue 17 Nov 14:32</span>
            </span>
          </div>
          <div className="laptop-screen">{children}</div>
          <div className="glass" aria-hidden="true" />
        </div>
        <img
          className="laptop-photo"
          src="/brand/laptop.webp"
          width={LAPTOP_W}
          height={LAPTOP_H}
          alt=""
          decoding="async"
        />
      </div>
    </Scaled>
  );
}
