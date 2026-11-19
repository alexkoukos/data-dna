import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { mask, scan, unmask } from "../src/detect/engine";
import { DEFAULT_POLICY, decideLocal } from "../src/detect/policy";

interface Case {
  name: string;
  text: string;
  expect: { entity: string; value: string }[];
  hidden?: boolean;
  signals?: string[];
}

const { cases } = JSON.parse(
  readFileSync(new URL("../../shared/fixtures/l1.json", import.meta.url), "utf-8"),
) as { cases: Case[] };

describe("L1 matches the shared fixtures (the brain test reads the same file)", () => {
  it.each(cases)("$name", (c) => {
    const result = scan(c.text);
    const got = [
      ...new Set(result.findings.map((f) => `${f.entity}:${f.value.replaceAll(" ", "")}`)),
    ].sort();
    const want = [
      ...new Set(c.expect.map((e) => `${e.entity}:${e.value.replaceAll(" ", "")}`)),
    ].sort();
    expect(got).toEqual(want);
    for (const s of c.signals ?? []) expect(result.signals).toContain(s);
    if (c.hidden) expect(result.findings.every((f) => f.hidden)).toBe(true);
  });
});

describe("mask and unmask", () => {
  it("replaces values, then restores them", () => {
    const text = "IBAN GR1601101250000000012300695 and AFM 123456783 ok";
    const result = scan(text);
    const masked = mask(result.text, result.findings);
    expect(masked.text).toBe("IBAN [IBAN_1] and AFM [AFM_1] ok");
    expect(unmask(`Sent to [IBAN_1] for [AFM_1]`, masked.placeholders)).toBe(
      "Sent to GR1601101250000000012300695 for 123456783",
    );
  });

  it("numbers repeated entities", () => {
    const r = scan("AFM 123456783 and again 123456783");
    expect(mask(r.text, r.findings).text).toBe("AFM [AFM_1] and again [AFM_2]");
  });
});

describe("local decision", () => {
  it("masks ids, escalates hidden values to warn, allows clean text", () => {
    expect(decideLocal(["greek_id"], DEFAULT_POLICY).action).toBe("mask");
    expect(decideLocal(["greek_id"], DEFAULT_POLICY, { hiddenFinding: true }).action).toBe("warn");
    expect(decideLocal([], DEFAULT_POLICY).action).toBe("allow");
    expect(decideLocal(["secret", "injection"], DEFAULT_POLICY).action).toBe("block");
  });
});

describe("speed", () => {
  it("checks a long prompt in well under 50 ms", () => {
    const text = "Please review this paragraph about quarterly planning. ".repeat(200);
    const t = performance.now();
    scan(text);
    expect(performance.now() - t).toBeLessThan(50);
  });
});

describe("client names from the policy", () => {
  const clients = ["Pindos Telecom", "Pindos", "HML", "Argo Shipping"];
  it("finds names and aliases", () => {
    const r = scan("Email pindos telecom and Argo Shipping about HML work", clients);
    expect(r.findings.map((f) => f.value)).toEqual(["pindos telecom", "Argo Shipping", "HML"]);
    expect(r.findings.every((f) => f.category === "client_name")).toBe(true);
  });
  it("does not match inside other words, or short aliases in the wrong case", () => {
    expect(scan("Pindosx and the hml file", clients).findings).toEqual([]);
  });
  it("keeps checksum findings and client names apart", () => {
    const r = scan("Argo Shipping paid GR1601101250000000012300695", clients);
    expect(r.findings.map((f) => f.entity).sort()).toEqual(["CLIENT", "IBAN"]);
  });
});
