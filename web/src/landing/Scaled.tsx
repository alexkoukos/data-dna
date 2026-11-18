import { useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

/**
 * Draws children at a fixed design size and scales them to fit the width they are given,
 * centred. `max` caps how far it may scale up (1 = never bigger than the design size).
 */
export function Scaled({
  width,
  height,
  max = 1,
  align = "center",
  children,
  className,
}: {
  width: number;
  height: number;
  max?: number;
  align?: "center" | "right";
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState({ scale: 0.5, left: 0 });

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const scale = Math.min(max, el.clientWidth / width) || 0.5;
      setFit({
        scale,
        left: Math.max(0, (el.clientWidth - width * scale) / (align === "right" ? 1 : 2)),
      });
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [width, max, align]);

  const outer: CSSProperties = { height: height * fit.scale };
  const inner: CSSProperties = {
    width,
    height,
    left: fit.left,
    transform: `scale(${fit.scale})`,
  };
  return (
    <div ref={ref} className={`scaled ${className ?? ""}`} style={outer}>
      <div className="scaled-inner" style={inner}>
        {children}
      </div>
    </div>
  );
}
