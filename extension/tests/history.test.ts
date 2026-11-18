import { describe, expect, it } from "vitest";
import { weekSeries } from "../src/history";

describe("weekSeries", () => {
  it("fills seven days, oldest first, with zeros for quiet days", () => {
    const end = new Date(Date.UTC(2026, 10, 18, 15));
    const s = weekSeries({ "2026-11-18": 4, "2026-11-16": 2, "2026-11-01": 9 }, end);
    expect(s.data).toEqual([0, 0, 0, 0, 2, 0, 4]);
    expect(s.total).toBe(6);
    expect(s.labels).toHaveLength(7);
  });

  it("copes with no history at all", () => {
    expect(weekSeries(undefined, new Date()).total).toBe(0);
  });
});

import { daysSeries } from "../src/history";

describe("daysSeries", () => {
  it("covers 30 days and labels them by date", () => {
    const end = new Date(Date.UTC(2026, 10, 18, 9));
    const s = daysSeries({ "2026-11-18": 3, "2026-10-20": 2 }, end, 30);
    expect(s.data).toHaveLength(30);
    expect(s.data.at(-1)).toBe(3);
    expect(s.data[0]).toBe(2);
    expect(s.total).toBe(5);
    expect(s.labels.at(-1)).toBe("18 Nov");
  });
});
