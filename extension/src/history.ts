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

/** Counts per day for the `days` days ending on `end` (UTC), oldest first. 7 days label as "Wed 18", longer as "18 Nov". */
export function daysSeries(
  counts: Record<string, number> | undefined,
  end: Date,
  days: number,
): WeekSeries {
  const data: number[] = [];
  const labels: string[] = [];
  for (let back = days - 1; back >= 0; back--) {
    const d = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate() - back));
    data.push(counts?.[d.toISOString().slice(0, 10)] ?? 0);
    labels.push(
      days <= 7
        ? `${d.toLocaleDateString("en", { weekday: "short", timeZone: "UTC" })} ${d.getUTCDate()}`
        : `${d.getUTCDate()} ${d.toLocaleDateString("en", { month: "short", timeZone: "UTC" })}`,
    );
  }
  return { data, labels, total: data.reduce((a, b) => a + b, 0) };
}
