export interface WeekSeries {
  data: number[];
  labels: string[];
  total: number;
}

/** Saves per day for the 7 days ending on `end` (UTC days, like the stored keys), oldest first. */
export function weekSeries(history: Record<string, number> | undefined, end: Date): WeekSeries {
  const data: number[] = [];
  const labels: string[] = [];
  for (let back = 6; back >= 0; back--) {
    const d = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate() - back));
    data.push(history?.[d.toISOString().slice(0, 10)] ?? 0);
    labels.push(
      `${d.toLocaleDateString("en", { weekday: "short", timeZone: "UTC" })} ${d.getUTCDate()}`,
    );
  }
  return { data, labels, total: data.reduce((a, b) => a + b, 0) };
}
