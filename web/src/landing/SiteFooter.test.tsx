import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchGateHealth } from "@/lib/healthApi";
import { SiteFooter } from "./SiteFooter";

const reply = (body: unknown, ok = true) =>
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok, json: () => Promise.resolve(body) }));

afterEach(() => vi.unstubAllGlobals());

describe("SiteFooter gate status", () => {
  it("says in words that the gate is online", async () => {
    reply({ status: "ok", database: "ok" });
    render(
      <MemoryRouter>
        <SiteFooter />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Gate online")).toBeInTheDocument();
  });

  it("says what to do when the gate is offline", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(
      <MemoryRouter>
        <SiteFooter />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Gate offline. Start it with make up.")).toBeInTheDocument();
  });
});

describe("fetchGateHealth", () => {
  it("is online when the brain and database answer", async () => {
    reply({ status: "ok", database: "ok" });
    expect(await fetchGateHealth()).toBe("online");
  });

  it("is degraded when the database is unreachable", async () => {
    reply({ status: "ok", database: "unreachable" });
    expect(await fetchGateHealth()).toBe("degraded");
  });

  it("is offline on an error status or a non-JSON reply", async () => {
    reply({}, false);
    expect(await fetchGateHealth()).toBe("offline");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.reject(new SyntaxError()) }),
    );
    expect(await fetchGateHealth()).toBe("offline");
  });
});
