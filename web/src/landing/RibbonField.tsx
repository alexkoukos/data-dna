import { useEffect, useRef } from "react";

// "Ribbon Field" gradient (21st.dev): a stripe field along `angle`, edges feathered by `softness`,
// bent by `wave` with a cross-axis sine offset: (wave / 100) * 0.35 * sin(cross * 2.4 * 2PI + clock).
// Drawn on a small canvas and scaled up by CSS (the gradient is smooth, so it stays soft).
// Animated from a requestAnimationFrame loop: ph = t * speed, and the wave clock runs from its
// start value 20.75 to 20.75 + ph * 1.2, so at ph = 0 it is exactly the still picture.
// With motionAmount 0 the angle does not sway, so only the ribbons flow.

const ANGLE = 32; // degrees
const SOFTNESS = 24;
const WAVE = 14;
const CLOCK0 = 20.75;
const SPEED = 1.0; // ph = t * SPEED
const MOTION_AMOUNT = 0; // angle + sin(spin * 0.6) * 28 * amt
const DIR = 1;

type RGB = [number, number, number];
const EGGSHELL: RGB = [0xff, 0xf1, 0xcf];
const GOLD: RGB = [0xf8, 0xb5, 0x00];
const VERMILION: RGB = [0xeb, 0x61, 0x01];
const AUBERGINE: RGB = [0x82, 0x48, 0x80];
// Band boundaries along the gradient line (the middle of each transition in the exported CSS).
const BOUNDS = [0.3514, 0.585, 0.7982];
const FEATHER = 0.004 + SOFTNESS * 0.0007;

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

function paint(ctx: CanvasRenderingContext2D, w: number, h: number, ph: number) {
  const spin = ph * DIR;
  const angle = ((ANGLE + Math.sin(spin * 0.6) * 28 * MOTION_AMOUNT) * Math.PI) / 180;
  const clock = CLOCK0 + ph * 1.2;
  const sa = Math.sin(angle);
  const ca = Math.cos(angle);
  const len = Math.abs(w * sa) + Math.abs(h * ca);
  const img = ctx.createImageData(w, h);
  const d = img.data;
  let i = 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const dx = x - w / 2;
      const dy = y - h / 2;
      const cross = (dx * ca + dy * sa) / len;
      let u = (dx * sa - dy * ca) / len + 0.5;
      u += (WAVE / 100) * 0.35 * Math.sin(cross * 2.4 * Math.PI * 2 + clock);
      const m1 = smooth(BOUNDS[0] - FEATHER, BOUNDS[0] + FEATHER, u);
      const m2 = smooth(BOUNDS[1] - FEATHER * 0.6, BOUNDS[1] + FEATHER * 0.6, u);
      const m3 = smooth(BOUNDS[2] - FEATHER * 0.4, BOUNDS[2] + FEATHER * 0.4, u);
      for (let k = 0; k < 3; k++) {
        let c = EGGSHELL[k];
        c += (GOLD[k] - c) * m1;
        c += (VERMILION[k] - c) * m2;
        c += (AUBERGINE[k] - c) * m3;
        d[i + k] = c;
      }
      d[i + 3] = 255;
      i += 4;
    }
  }
  ctx.putImageData(img, 0, 0);
}

export function RibbonField({ className = "" }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let visible = true;
    let t0 = performance.now();
    let w = 0;
    let h = 0;

    const size = () => {
      const r = canvas.getBoundingClientRect();
      // a quarter of the size is plenty for a smooth gradient, and keeps every frame cheap
      w = Math.max(64, Math.round(r.width / 4));
      h = Math.max(64, Math.round(r.height / 4));
      canvas.width = w;
      canvas.height = h;
      paint(ctx, w, h, 0);
    };
    const frame = (now: number) => {
      raf = 0;
      if (!visible || document.hidden) return;
      paint(ctx, w, h, ((now - t0) / 1000) * SPEED);
      raf = requestAnimationFrame(frame);
    };
    const start = () => {
      if (reduce || raf) return;
      t0 = performance.now() - 0; // restart the clock, so there is no jump
      raf = requestAnimationFrame(frame);
    };

    size();
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      if (visible) start();
      else if (raf) {
        cancelAnimationFrame(raf);
        raf = 0;
      }
    });
    io.observe(canvas);
    const ro = new ResizeObserver(size);
    ro.observe(canvas);
    const onVis = () => {
      if (!document.hidden) start();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      if (raf) cancelAnimationFrame(raf);
      io.disconnect();
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  return (
    <div className={`ribbon ${className}`.trim()} aria-hidden="true">
      <canvas ref={ref} className="ribbon-canvas" />
      <span className="ribbon-grain" />
    </div>
  );
}
