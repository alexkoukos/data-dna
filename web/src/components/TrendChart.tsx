import { useEffect, useId, useRef, useState } from "react";

/** One calm, flat area chart: baseline at zero, hairline grid, a smooth line, the peak marked.
 * Pointer or arrow keys read a single point. No canvas, no animation loop. */
export interface TrendChartProps {
  data: number[];
  labels: string[];
  /** Line and fill colour. */
  accent?: string;
  height?: number;
  /** Spoken summary, e.g. "Incidents per day, last 7 days". */
  summary: string;
  /** Shown after the number in the readout, e.g. "incidents". */
  unit?: string;
}

const PAD = { top: 18, right: 10, bottom: 24, left: 10 };

const at0 = (a: ArrayLike<number>, i: number) => a[i] ?? 0;

/** Smooth, never-overshooting curve through the points (Fritsch-Carlson tangents). */
function curve(xs: number[], ys: number[]) {
  const n = xs.length;
  if (n === 1) return `M${at0(xs, 0)} ${at0(ys, 0)}`;
  const d = Array.from(
    { length: n - 1 },
    (_, i) => (at0(ys, i + 1) - at0(ys, i)) / (at0(xs, i + 1) - at0(xs, i)),
  );
  const m = new Array<number>(n).fill(0);
  m[0] = at0(d, 0);
  m[n - 1] = at0(d, n - 2);
  for (let i = 1; i < n - 1; i++) {
    const p = at0(d, i - 1);
    const q = at0(d, i);
    m[i] = p * q <= 0 ? 0 : (p + q) / 2;
  }
  for (let i = 0; i < n - 1; i++) {
    const di = at0(d, i);
    if (di === 0) {
      m[i] = 0;
      m[i + 1] = 0;
    } else {
      const a = at0(m, i) / di;
      const b = at0(m, i + 1) / di;
      const s = a * a + b * b;
      if (s > 9) {
        const t = 3 / Math.sqrt(s);
        m[i] = t * a * di;
        m[i + 1] = t * b * di;
      }
    }
  }
  let p = `M${at0(xs, 0)} ${at0(ys, 0)}`;
  for (let i = 0; i < n - 1; i++) {
    const dx = (at0(xs, i + 1) - at0(xs, i)) / 3;
    p += ` C${at0(xs, i) + dx} ${at0(ys, i) + at0(m, i) * dx} ${at0(xs, i + 1) - dx} ${at0(ys, i + 1) - at0(m, i + 1) * dx} ${at0(xs, i + 1)} ${at0(ys, i + 1)}`;
  }
  return p;
}

export function TrendChart({
  data,
  labels,
  accent = "#f59e0b",
  height = 150,
  summary,
  unit = "",
}: TrendChartProps) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(320);
  const [hover, setHover] = useState<number | null>(null);
  const uid = useId().replace(/:/g, "");

  useEffect(() => {
    const el = box.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const update = () => setWidth(Math.max(160, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const n = data.length;
  const max = Math.max(1, ...data);
  const top = Math.ceil(max * 1.15);
  const innerW = width - PAD.left - PAD.right;
  const innerH = height - PAD.top - PAD.bottom;
  const x = (i: number) => PAD.left + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const y = (v: number) => PAD.top + innerH - (v / top) * innerH;
  const xs = data.map((_, i) => x(i));
  const ys = data.map((v) => y(v));
  const line = curve(xs.length ? xs : [0], ys.length ? ys : [0]);
  const base = PAD.top + innerH;
  const area = `${line} L${at0(xs, n - 1)} ${base} L${at0(xs, 0)} ${base} Z`;
  const peak = data.indexOf(max);
  const shown = hover ?? null;
  const tickEvery = Math.max(1, Math.ceil(n / 6));

  const at = (clientX: number) => {
    const r = box.current?.getBoundingClientRect();
    if (!r || n === 0) return;
    const rel =
      ((clientX - r.left - PAD.left) / Math.max(1, r.width - PAD.left - PAD.right)) * (n - 1);
    setHover(Math.max(0, Math.min(n - 1, Math.round(rel))));
  };

  return (
    <div ref={box} style={{ width: "100%" }}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={summary}
        tabIndex={0}
        style={{ display: "block", overflow: "visible", touchAction: "pan-y", outlineOffset: 4 }}
        onPointerMove={(e) => at(e.clientX)}
        onPointerLeave={() => setHover(null)}
        onFocus={() => setHover((h) => h ?? peak)}
        onBlur={() => setHover(null)}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") setHover((h) => Math.max(0, (h ?? peak) - 1));
          else if (e.key === "ArrowRight") setHover((h) => Math.min(n - 1, (h ?? peak) + 1));
          else if (e.key === "Escape") setHover(null);
        }}
      >
        <defs>
          <linearGradient id={`fill-${uid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity="0.28" />
            <stop offset="100%" stopColor={accent} stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((f) => (
          <line
            key={f}
            x1={PAD.left}
            x2={width - PAD.right}
            y1={PAD.top + innerH * f}
            y2={PAD.top + innerH * f}
            stroke="var(--tc-grid, #e5e7eb)"
            strokeWidth="1"
            strokeDasharray={f === 1 ? undefined : "3 4"}
          />
        ))}
        {n > 0 && (
          <>
            <path d={area} fill={`url(#fill-${uid})`} />
            <path
              d={line}
              fill="none"
              stroke={accent}
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </>
        )}
        {labels.map((l, i) =>
          i % tickEvery === 0 || i === n - 1 ? (
            <text
              key={i}
              x={x(i)}
              y={height - 6}
              textAnchor={i === 0 ? "start" : i === n - 1 ? "end" : "middle"}
              fontSize="11"
              fill="var(--tc-muted, #6b7280)"
            >
              {l}
            </text>
          ) : null,
        )}
        {n > 0 && shown === null && at0(data, peak) > 0 && (
          <g>
            <circle
              cx={at0(xs, peak)}
              cy={at0(ys, peak)}
              r="5"
              fill="var(--tc-bg, #fff)"
              stroke={accent}
              strokeWidth="2.5"
            />
            <text
              x={Math.min(Math.max(at0(xs, peak), 22), width - 22)}
              y={at0(ys, peak) - 11}
              textAnchor="middle"
              fontSize="11"
              fontWeight="700"
              fill="var(--tc-fg, #262626)"
            >
              {at0(data, peak)}
            </text>
          </g>
        )}
        {shown !== null && n > 0 && (
          <g>
            <line
              x1={at0(xs, shown)}
              x2={at0(xs, shown)}
              y1={PAD.top}
              y2={base}
              stroke="var(--tc-fg, #262626)"
              strokeOpacity="0.25"
            />
            <circle
              cx={at0(xs, shown)}
              cy={at0(ys, shown)}
              r="5"
              fill="var(--tc-bg, #fff)"
              stroke={accent}
              strokeWidth="2.5"
            />
            <g
              transform={`translate(${Math.min(Math.max(at0(xs, shown), 56), width - 56)} ${Math.max(at0(ys, shown) - 14, 16)})`}
            >
              <rect x="-52" y="-30" width="104" height="38" rx="9" fill="var(--tc-fg, #262626)" />
              <text
                x="0"
                y="-15"
                textAnchor="middle"
                fontSize="12"
                fontWeight="700"
                fill="var(--tc-bg, #fff)"
              >
                {at0(data, shown)} {unit}
              </text>
              <text
                x="0"
                y="1"
                textAnchor="middle"
                fontSize="10.5"
                fill="var(--tc-bg, #fff)"
                fillOpacity="0.75"
              >
                {labels[shown] ?? ""}
              </text>
            </g>
          </g>
        )}
      </svg>
      {/* A table ignores the 1 px width of sr-only and stretches the page on a phone, so the
          visually hidden box is a div that clips it. Screen readers still read the table. */}
      <div className="sr-only">
        <table>
          <caption>{summary}</caption>
          <tbody>
            {labels.map((l, i) => (
              <tr key={i}>
                <th scope="row">{l}</th>
                <td>{at0(data, i)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
