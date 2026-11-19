import { useEffect, useRef } from "react";

export const APP_FOOTER_ID = "app-footer";
const GAP = 8;

/** For an element fixed to the bottom of the screen: when the app footer scrolls into view, lift the
 * element by exactly the overlap so it never covers the footer's links. Works in either corner and
 * at any `bottom` offset. Pass `deps` that swap the element or change the layout (route, mode). */
export function useLiftAboveFooter<T extends HTMLElement>(deps: unknown[]) {
  const ref = useRef<T>(null);

  useEffect(() => {
    let frame = 0;
    const place = () => {
      frame = 0;
      const el = ref.current;
      const footer = document.getElementById(APP_FOOTER_ID);
      if (!el) return;
      if (!footer) {
        el.style.transform = "";
        return;
      }
      const base = parseFloat(getComputedStyle(el).bottom) || 0;
      const overlap = window.innerHeight - footer.getBoundingClientRect().top;
      const lift = Math.max(0, Math.ceil(overlap + GAP - base));
      el.style.transform = lift > 0 ? `translateY(-${lift}px)` : "";
    };
    const schedule = () => {
      if (!frame) frame = window.requestAnimationFrame(place);
    };
    place();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    // Content that loads after the first paint moves the footer without a scroll.
    const ro = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(schedule);
    ro?.observe(document.body);
    return () => {
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      ro?.disconnect();
      window.cancelAnimationFrame(frame);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return ref;
}
