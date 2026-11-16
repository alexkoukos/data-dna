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
    expect(screen.getByRole("link", { name: "Start the demo" })).toHaveAttribute("href", "/chat");
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Open the security view" })).toHaveAttribute(
      "href",
      "/security/incidents",
    );
  });
});
