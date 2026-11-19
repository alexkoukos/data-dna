import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import HomePage from "./HomePage";

describe("HomePage", () => {
  it("offers one clear start, lists every app tool", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    const start = screen.getAllByRole("link", { name: "Get the extension" });
    expect(start.length).toBeGreaterThan(0);
    for (const link of start) expect(link).toHaveAttribute("href", "/extension");
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
    for (const name of ["Try to break it", "Company AI", "Security", "Connect a tool"]) {
      expect(screen.getAllByRole("link", { name: new RegExp(name) }).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole("link", { name: "Or jump to the security view" })).toHaveAttribute(
      "href",
      "/security",
    );
  });
});
