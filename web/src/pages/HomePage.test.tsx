import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import HomePage from "./HomePage";

describe("HomePage", () => {
  it("offers one clear start and the three demo steps", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    const start = screen.getAllByRole("link", { name: "Get the extension" });
    expect(start.length).toBeGreaterThan(0);
    for (const link of start) expect(link).toHaveAttribute("href", "/extension");
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Open the security view" })).toHaveAttribute(
      "href",
      "/security/incidents",
    );
  });
});
