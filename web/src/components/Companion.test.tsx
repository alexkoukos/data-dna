import { MemoryRouter } from "react-router-dom";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { announce, announceError } from "../lib/companion";
import { Companion, VISIBLE_MS } from "./Companion";

vi.mock("../lib/securityApi", () => ({
  fetchIncidents: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}));

function setup() {
  render(
    <MemoryRouter>
      <Companion />
    </MemoryRouter>,
  );
}

describe("Companion", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.useRealTimers());

  it("is hidden until something happens", () => {
    setup();
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    act(() => announce("block"));
    expect(screen.getByRole("complementary", { name: /thyro/i })).toBeInTheDocument();
  });

  it("starts in the bottom right and moves to the left", async () => {
    setup();
    act(() => announce("allow"));
    const aside = screen.getByRole("complementary", { name: /thyro/i });
    expect(aside.className).toContain("right-4");
    await userEvent.click(screen.getByRole("button", { name: /bottom left/i }));
    expect(aside.className).toContain("left-4");
    expect(JSON.parse(localStorage.getItem("pyli.companion") ?? "{}").corner).toBe("left");
  });

  it("says what the gate decided, with the label", () => {
    setup();
    act(() => announce("block"));
    expect(screen.getByText("Blocked. The gate stays shut.")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
  });

  it("says what went wrong and what to do next", () => {
    setup();
    act(() => announceError("That did not go through. Your message is back in the box."));
    expect(screen.getByText(/did not go through/)).toBeInTheDocument();
  });

  it("leaves by itself after six seconds", () => {
    vi.useFakeTimers();
    setup();
    act(() => announce("mask"));
    expect(screen.getByRole("complementary")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(VISIBLE_MS));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("can be collapsed and shown again, and has no pop-out button", async () => {
    setup();
    act(() => announce("warn"));
    expect(screen.queryByRole("button", { name: /float|picture/i })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Hide Thyro" }));
    expect(screen.queryByText("Warned")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show Thyro" }));
    expect(screen.getByText("Warned")).toBeInTheDocument();
  });
});
