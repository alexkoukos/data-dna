import { describe, expect, it } from "vitest";
import { STATES, line } from "./copy";

describe("mascot copy", () => {
  it("has English and Greek for every state, within 80 characters", () => {
    expect(STATES).toEqual(
      expect.arrayContaining([
        "idle",
        "allow",
        "warn",
        "mask",
        "local",
        "block",
        "thinking",
        "empty",
        "error",
      ]),
    );
    for (const s of STATES)
      for (const l of ["en", "el"] as const) {
        const t = line(s, l);
        expect(t.length).toBeGreaterThan(0);
        expect(t.length).toBeLessThanOrEqual(80);
      }
  });
  it("never uses exclamation marks", () => {
    for (const s of STATES) expect(line(s, "en")).not.toContain("!");
  });
});
