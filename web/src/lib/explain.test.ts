import { describe, expect, it } from "vitest";
import { explainReason } from "./explain";

describe("explainReason", () => {
  it("turns brain reasons into plain sentences", () => {
    expect(explainReason("Contains greek id")).toBe(
      "Your message contains a Greek ID number (AFM or AMKA).",
    );
    expect(explainReason("Matches a restricted document")).toBe(
      "It matches a restricted company document.",
    );
    expect(explainReason("Evasion attempt detected: spaced_digits")).toMatch(/spaced out/);
  });
  it("falls back to the original text for unknown reasons", () => {
    expect(explainReason("Something new")).toBe("Something new");
  });
});
