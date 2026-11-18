import { describe, expect, it } from "vitest";
import type { Decision } from "./securityApi";
import { buildSeries, direction, isSave } from "./trends";

const end = new Date(2026, 10, 18, 15, 0);
const row = (d: Date, decision: Decision = "block") => ({ ts: d.toISOString(), decision });

describe("buildSeries", () => {
  it("counts rows into the last 7 days, newest last", () => {
    const rows = [
      row(new Date(2026, 10, 18, 9)),
      row(new Date(2026, 10, 18, 11)),
      row(new Date(2026, 10, 16, 9)),
      row(new Date(2026, 10, 1, 9)),
    ];
    const s = buildSeries(rows, "Weekly", end);
    expect(s.data).toEqual([0, 0, 0, 0, 1, 0, 2]);
    expect(s.total).toBe(3);
    expect(s.labels).toHaveLength(7);
  });

  it("groups the yearly view by month", () => {
    const rows = [
      row(new Date(2026, 10, 3)),
      row(new Date(2026, 9, 20)),
      row(new Date(2025, 0, 5)),
    ];
    const s = buildSeries(rows, "Yearly", end);
    expect(s.data.at(-1)).toBe(1);
    expect(s.data.at(-2)).toBe(1);
    expect(s.total).toBe(2);
  });

  it("only counts rows the picker accepts", () => {
    const rows = [row(end, "mask"), row(end, "allow"), row(end, "warn")];
    expect(buildSeries(rows, "Weekly", end, isSave).total).toBe(1);
  });

  it("ignores rows with a broken timestamp", () => {
    expect(buildSeries([{ ts: "nope", decision: "block" }], "Weekly", end).total).toBe(0);
  });
});

describe("direction", () => {
  it("compares the later half with the earlier half", () => {
    expect(direction([1, 1, 5, 5])).toBe("up");
    expect(direction([5, 5, 1, 1])).toBe("down");
    expect(direction([2, 2, 2, 2])).toBe("none");
  });
});
