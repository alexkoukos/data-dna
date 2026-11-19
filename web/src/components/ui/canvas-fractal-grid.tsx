import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useAnimation, useReducedMotion } from "motion/react";

interface GradientStop {
  color: string;
  position: number;
}

export interface GradientType {
  stops: GradientStop[];
  centerX: number;
  centerY: number;
}

type Performance = "low" | "medium" | "high";

export interface CanvasFractalGridProps {
  /** Size of each dot in pixels */
  dotSize?: number;
  /** Spacing between dots in pixels */
  dotSpacing?: number;
  /** Opacity of dots (0-1) */
  dotOpacity?: number;
  /** Duration of the background gradient animation in seconds */
  gradientAnimationDuration?: number;
  /** Intensity of the wave effect near the pointer */
  waveIntensity?: number;
  /** Radius of the wave effect in pixels */
  waveRadius?: number;
  /** Gradient layers drawn behind the dots */
  gradients?: GradientType[];
  /** Colour of the dots, as hex, rgb() or rgba() */
  dotColor?: string;
  /** Colour of the glow near the pointer, as hex, rgb() or rgba() */
  glowColor?: string;
  enableNoise?: boolean;
  /** Opacity of the noise overlay (0-1) */
  noiseOpacity?: number;
  enableMouseGlow?: boolean;
  initialPerformance?: Performance;
  enableGradient?: boolean;
  /** Fill the nearest positioned parent instead of the whole screen */
  contained?: boolean;
  className?: string;
}

/** "rgba(245, 158, 11, 1)" and a new alpha give "rgba(245, 158, 11, a)". */
function withAlpha(color: string, alpha: number): string {
  const hex = color.match(/^#([0-9a-f]{6})/i);
  if (hex) {
    const n = parseInt(hex[1], 16);
    return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${Math.max(0, Math.min(1, alpha))})`;
  }
  const m = color.match(/rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/);
  return m ? `rgba(${m[1]}, ${m[2]}, ${m[3]}, ${Math.max(0, Math.min(1, alpha))})` : color;
}

const NoiseOverlay = React.memo(function NoiseOverlay({ opacity }: { opacity: number }) {
  return (
    <div className="absolute inset-0 h-full w-full mix-blend-overlay" style={{ opacity }}>
      <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
        <filter id="sentry-noise">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.65"
            numOctaves="3"
            stitchTiles="stitch"
          />
        </filter>
        <rect width="100%" height="100%" filter="url(#sentry-noise)" />
      </svg>
    </div>
  );
});

function useBreakpoint() {
  const [width, setWidth] = useState(() =>
    typeof window === "undefined" ? 1280 : window.innerWidth,
  );
  useEffect(() => {
    const on = () => setWidth(window.innerWidth);
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  return { isMobile: width < 768, isTablet: width >= 768 && width < 1024 };
}

/** Drops detail when the frame rate falls, so a slow machine stays usable. */
function usePerformance(initial: Performance) {
  const [performance, setPerformance] = useState<Performance>(initial);
  useEffect(() => {
    let frames = 0;
    let last = globalThis.performance.now();
    let id = 0;
    const tick = (t: number) => {
      frames++;
      if (t - last > 1000) {
        const fps = (frames * 1000) / (t - last);
        setPerformance(fps < 30 ? "low" : fps < 50 ? "medium" : "high");
        frames = 0;
        last = t;
      }
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, []);
  return performance;
}

const GradientLayer = React.memo(function GradientLayer({
  gradients,
  duration,
}: {
  gradients: GradientType[];
  duration: number;
}) {
  const controls = useAnimation();
  useEffect(() => {
    void controls.start({
      background: gradients.map(
        (g) =>
          `radial-gradient(circle at ${g.centerX}% ${g.centerY}%, ${g.stops
            .map((s) => `${s.color} ${s.position}%`)
            .join(", ")})`,
      ),
      transition: { duration, repeat: Infinity, repeatType: "reverse", ease: "linear" },
    });
  }, [controls, gradients, duration]);
  return <motion.div className="absolute inset-0 h-full w-full" animate={controls} />;
});

const SKIP: Record<Performance, number> = { low: 3, medium: 2, high: 1 };

function DotCanvas({
  dotSize,
  dotSpacing,
  dotOpacity,
  waveIntensity,
  waveRadius,
  dotColor,
  glowColor,
  performance,
  mouse,
  still,
}: {
  dotSize: number;
  dotSpacing: number;
  dotOpacity: number;
  waveIntensity: number;
  waveRadius: number;
  dotColor: string;
  glowColor: string;
  performance: Performance;
  mouse: React.RefObject<{ x: number; y: number }>;
  still: boolean;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const resize = () => {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
    };
    resize();
    const ro = typeof ResizeObserver === "function" ? new ResizeObserver(resize) : null;
    ro?.observe(canvas);
    window.addEventListener("resize", resize);

    const idle = withAlpha(dotColor, dotOpacity);
    const draw = (time: number) => {
      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);
      const skip = SKIP[performance];
      const cols = Math.ceil(width / dotSpacing);
      const rows = Math.ceil(height / dotSpacing);
      const m = mouse.current;
      const cx = m.x * width;
      const cy = m.y * height;
      for (let i = 0; i < cols; i += skip) {
        for (let j = 0; j < rows; j += skip) {
          const x = i * dotSpacing;
          const y = j * dotSpacing;
          const dx = x - cx;
          const dy = y - cy;
          const distance = Math.hypot(dx, dy);
          let px = x;
          let py = y;
          if (!still && distance < waveRadius) {
            const strength = (1 - distance / waveRadius) ** 2;
            const angle = Math.atan2(dy, dx);
            const offset = Math.sin(distance * 0.05 - time * 0.005) * waveIntensity * strength;
            px += Math.cos(angle) * offset;
            py += Math.sin(angle) * offset;
            const g = ctx.createRadialGradient(px, py, 0, px, py, dotSize * (1 + strength));
            g.addColorStop(0, withAlpha(glowColor, dotOpacity * (1 + strength)));
            g.addColorStop(1, withAlpha(glowColor, 0));
            ctx.fillStyle = g;
          } else {
            ctx.fillStyle = idle;
          }
          ctx.beginPath();
          ctx.arc(px, py, dotSize / 2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    };

    let id = 0;
    let last = 0;
    if (still) {
      draw(0);
    } else {
      const loop = (t: number) => {
        if (t - last > 16) {
          draw(t);
          last = t;
        }
        id = requestAnimationFrame(loop);
      };
      id = requestAnimationFrame(loop);
    }
    const redraw = () => still && draw(0);
    window.addEventListener("resize", redraw);
    return () => {
      cancelAnimationFrame(id);
      ro?.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("resize", redraw);
    };
  }, [
    dotSize,
    dotSpacing,
    dotOpacity,
    waveIntensity,
    waveRadius,
    dotColor,
    glowColor,
    performance,
    mouse,
    still,
  ]);

  return <canvas ref={ref} className="absolute inset-0 h-full w-full" />;
}

const MouseGlow = React.memo(function MouseGlow({
  glowColor,
  pos,
}: {
  glowColor: string;
  pos: { x: number; y: number };
}) {
  const at = {
    left: `${pos.x * 100}%`,
    top: `${pos.y * 100}%`,
    transform: "translate(-50%, -50%)",
  };
  return (
    <>
      <div
        className="pointer-events-none absolute h-40 w-40 rounded-full"
        style={{
          ...at,
          filter: "blur(10px)",
          background: `radial-gradient(circle, ${withAlpha(glowColor, 0.2)} 0%, ${withAlpha(glowColor, 0)} 70%)`,
        }}
      />
      <div
        className="pointer-events-none absolute h-20 w-20 rounded-full"
        style={{
          ...at,
          background: `radial-gradient(circle, ${withAlpha(glowColor, 0.4)} 0%, ${withAlpha(glowColor, 0)} 70%)`,
        }}
      />
    </>
  );
});

/** Optional amber glow layers, off by default: the page is plain black with amber dots. */
export const sentryGradients: GradientType[] = [
  {
    stops: [
      { color: "rgba(245, 158, 11, 0.22)", position: 0 },
      { color: "rgba(180, 83, 9, 0.12)", position: 30 },
      { color: "transparent", position: 70 },
    ],
    centerX: 70,
    centerY: 30,
  },
  {
    stops: [
      { color: "rgba(124, 74, 6, 0.22)", position: 0 },
      { color: "rgba(245, 158, 11, 0.08)", position: 30 },
      { color: "transparent", position: 70 },
    ],
    centerX: 30,
    centerY: 70,
  },
];

export function CanvasFractalGrid({
  dotSize = 2,
  dotSpacing = 8,
  dotOpacity = 0.6,
  gradientAnimationDuration = 5,
  waveIntensity = 34,
  waveRadius = 70,
  gradients = sentryGradients,
  dotColor = "#ffa60d",
  glowColor = "#ffa60d",
  enableNoise = true,
  noiseOpacity = 0.05,
  enableMouseGlow = false,
  initialPerformance = "high",
  enableGradient = false,
  contained = false,
  className = "",
}: CanvasFractalGridProps) {
  const { isMobile, isTablet } = useBreakpoint();
  const performance = usePerformance(initialPerformance);
  const reduced = useReducedMotion() ?? false;
  const box = useRef<HTMLDivElement>(null);
  const mouse = useRef({ x: -1, y: -1 });
  const [glowPos, setGlowPos] = useState({ x: -1, y: -1 });

  const onMove = useCallback((e: MouseEvent) => {
    const r = box.current?.getBoundingClientRect();
    const p = r
      ? { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height }
      : { x: -1, y: -1 };
    mouse.current = p;
    setGlowPos(p);
  }, []);
  useEffect(() => {
    if (reduced) return;
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, [onMove, reduced]);

  const size = useMemo(
    () => (isMobile ? dotSize * 0.75 : isTablet ? dotSize * 0.9 : dotSize),
    [isMobile, isTablet, dotSize],
  );
  const spacing = useMemo(
    () => (isMobile ? dotSpacing * 1.5 : isTablet ? dotSpacing * 1.25 : dotSpacing),
    [isMobile, isTablet, dotSpacing],
  );

  return (
    <AnimatePresence>
      <motion.div
        key="sentry-grid"
        ref={box}
        aria-hidden="true"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 1.5, ease: "easeOut" }}
        className={`pointer-events-none ${contained ? "absolute" : "fixed"} inset-0 -z-10 h-full w-full overflow-hidden ${className}`.trim()}
      >
        {enableGradient && !reduced && (
          <GradientLayer gradients={gradients} duration={gradientAnimationDuration} />
        )}
        <DotCanvas
          dotSize={size}
          dotSpacing={spacing}
          dotOpacity={dotOpacity}
          waveIntensity={waveIntensity}
          waveRadius={waveRadius}
          dotColor={dotColor}
          glowColor={glowColor}
          performance={performance}
          mouse={mouse}
          still={reduced}
        />
        {enableNoise && <NoiseOverlay opacity={noiseOpacity} />}
        {enableMouseGlow && !reduced && glowPos.x >= 0 && (
          <MouseGlow glowColor={glowColor} pos={glowPos} />
        )}
      </motion.div>
    </AnimatePresence>
  );
}

export default React.memo(CanvasFractalGrid);
