import type { Decision } from "./securityApi";

export const PERIODS = ["Weekly", "Monthly", "Yearly"] as const;
export type Period = (typeof PERIODS)[number];

export interface Series {
  data: number[];
  labels: string[];
  /** The day (or first of the month) each bucket starts, as YYYY-MM-DD. */
  dates: string[];
  total: number;
}

interface Row {
  ts: string;
  decision: Decision;
}

const DAY = 86_400_000;
const iso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/**
 * Counts rows into evenly spaced buckets that end on `end`: 7 days, 30 days or 12 months.
 * `pick` chooses which rows count, so one list of incidents feeds every card.
 */
export function buildSeries(
  rows: Row[],
  period: Period,
  end: Date,
  pick: (r: Row) => boolean = () => true,
): Series {
  const monthly = period === "Yearly";
  const n = period === "Weekly" ? 7 : period === "Monthly" ? 30 : 12;
  const data = new Array<number>(n).fill(0);
  const last = startOfDay(end);
  const labels = Array.from({ length: n }, (_, i) => {
    const back = n - 1 - i;
    if (monthly) {
      const d = new Date(last.getFullYear(), last.getMonth() - back, 1);
      return d.toLocaleDateString("en", { month: "short" });
    }
    const d = new Date(last.getTime() - back * DAY);
    return period === "Weekly"
      ? `${d.toLocaleDateString("en", { weekday: "short" })} ${d.getDate()}`
      : `${d.getDate()} ${d.toLocaleDateString("en", { month: "short" })}`;
  });
  const dates = Array.from({ length: n }, (_, i) => {
    const back = n - 1 - i;
    return iso(
      monthly
        ? new Date(last.getFullYear(), last.getMonth() - back, 1)
        : new Date(last.getTime() - back * DAY),
    );
  });
  for (const r of rows) {
    if (!pick(r)) continue;
    const t = new Date(r.ts);
    if (Number.isNaN(t.getTime())) continue;
    const back = monthly
      ? (last.getFullYear() - t.getFullYear()) * 12 + (last.getMonth() - t.getMonth())
      : Math.round((last.getTime() - startOfDay(t).getTime()) / DAY);
    const idx = n - 1 - back;
    if (idx >= 0 && idx < n) data[idx] += 1;
  }
  return { data, labels, dates, total: data.reduce((a, b) => a + b, 0) };
}

/** "up" when the later half of the series is higher than the earlier half, "down" when lower. */
export function direction(data: number[]): "up" | "down" | "none" {
  const mid = Math.floor(data.length / 2);
  const a = data.slice(0, mid).reduce((x, y) => x + y, 0);
  const b = data.slice(mid).reduce((x, y) => x + y, 0);
  return b > a ? "up" : b < a ? "down" : "none";
}

/** Rows that kept something from leaving: masked, blocked or answered locally. */
export const isSave = (r: { decision: Decision }) =>
  r.decision === "mask" || r.decision === "block" || r.decision === "local";
