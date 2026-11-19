import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchGateHealth } from "../lib/healthApi";
import { AppFooter } from "./AppFooter";

function renderFooter(status: Parameters<typeof AppFooter>[0]["status"]) {
  render(
    <MemoryRouter>
      <AppFooter status={status} />
    </MemoryRouter>,
  );
}

describe("AppFooter", () => {
  it.each([
    ["checking", "Checking the gate"],
    ["online", "Gate online"],
    ["degraded", "Gate online, database unreachable. Run make up."],
    ["offline", "Gate offline. Start it with make up."],
  ] as const)("says %s in words, not only color", (status, text) => {
    renderFooter(status);
    expect(screen.getByRole("status")).toHaveTextContent(text);
  });

  it("links to the landing page and opens GitHub safely in a new tab", () => {
    renderFooter("online");
    expect(screen.getByRole("link", { name: "About Pyli" })).toHaveAttribute("href", "/");
    const gh = screen.getByRole("link", { name: /GitHub/ });
    expect(gh).toHaveAttribute("target", "_blank");
    expect(gh).toHaveAttribute("rel", "noopener noreferrer");
  });
});

describe("fetchGateHealth", () => {
  afterEach(() => vi.unstubAllGlobals());

  const reply = (body: unknown, ok = true) =>
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok, json: () => Promise.resolve(body) }));

  it("is online when the brain and database answer", async () => {
    reply({ status: "ok", database: "ok" });
    expect(await fetchGateHealth()).toBe("online");
  });

  it("is degraded when the database is unreachable", async () => {
    reply({ status: "ok", database: "unreachable" });
    expect(await fetchGateHealth()).toBe("degraded");
  });

  it("is offline on an error status, a non-JSON reply or a network failure", async () => {
    reply({}, false);
    expect(await fetchGateHealth()).toBe("offline");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.reject(new SyntaxError()) }),
    );
    expect(await fetchGateHealth()).toBe("offline");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    expect(await fetchGateHealth()).toBe("offline");
  });
});
