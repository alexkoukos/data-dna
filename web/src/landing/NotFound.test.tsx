import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import NotFound from "./NotFound";

describe("NotFound", () => {
  it("says nothing was found, shows the address and links home", () => {
    render(
      <MemoryRouter initialEntries={["/no/such/page"]}>
        <NotFound />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "Nothing here." })).toBeInTheDocument();
    expect(screen.getByText("/no/such/page")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to the start" })).toHaveAttribute("href", "/");
  });
});
