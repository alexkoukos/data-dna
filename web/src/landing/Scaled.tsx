import { useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

/** Draws children at a fixed design size and scales them to fit the width they are given. */
export function Scaled({
  width,
  height,
  children,
  className,
}: {
  width: number;
  height: number;
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.5);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setScale(Math.min(1, el.clientWidth / width) || 0.5);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [width]);

  const outer: CSSProperties = { aspectRatio: `${width} / ${height}` };
  const inner: CSSProperties = { width, height, transform: `scale(${scale})` };
  return (
    <div ref={ref} className={`scaled ${className ?? ""}`} style={outer}>
      <div className="scaled-inner" style={inner}>
        {children}
      </div>
    </div>
  );
}
