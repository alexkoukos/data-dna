import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders main navigation", () => {
    render(
      <MemoryRouter initialEntries={["/app"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Main" });
    for (const name of ["How it works", "Developers", "Company AI", "Live demo"]) {
      expect(within(nav).getByRole("link", { name })).toBeInTheDocument();
    }
  });
});
