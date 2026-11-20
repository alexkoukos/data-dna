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
    // One card per tool, each a single link named by its title, with a short checklist.
    expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(5);
    expect(screen.getByRole("link", { name: "Company AI" })).toHaveAttribute("href", "/chat");
    expect(screen.getByText("Attach PDF, Word or images")).toBeInTheDocument();
    for (const name of ["Try to break it", "Company AI", "Security", "Connect a tool"]) {
      expect(screen.getAllByRole("link", { name: new RegExp(name) }).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole("link", { name: "Or jump to the security view" })).toHaveAttribute(
      "href",
      "/security",
    );
  });
});
