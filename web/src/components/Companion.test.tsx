import { MemoryRouter } from "react-router-dom";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { announce } from "../lib/companion";
import { Companion } from "./Companion";

vi.mock("../lib/securityApi", () => ({
  fetchIncidents: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}));

describe("Companion", () => {
  beforeEach(() => localStorage.clear());

  it("starts in the bottom right and moves to the left", async () => {
    render(
      <MemoryRouter>
        <Companion />
      </MemoryRouter>,
    );
    const aside = screen.getByRole("complementary", { name: /thyro/i });
    expect(aside.className).toContain("right-4");
    await userEvent.click(screen.getByRole("button", { name: /bottom left/i }));
    expect(aside.className).toContain("left-4");
    expect(JSON.parse(localStorage.getItem("pyli.companion") ?? "{}").corner).toBe("left");
  });

  it("says what the gate decided, with the label", () => {
    render(
      <MemoryRouter>
        <Companion />
      </MemoryRouter>,
    );
    act(() => announce("block"));
    expect(screen.getByText("Blocked. The gate stays shut.")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
  });

  it("can be hidden and shown again", async () => {
    render(
      <MemoryRouter>
        <Companion />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Hide Thyro" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show Thyro" }));
    expect(screen.getByRole("complementary")).toBeInTheDocument();
  });
});
