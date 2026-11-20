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
    for (const name of ["How it works", "Company AI", "Live demo"]) {
      expect(within(nav).getByRole("link", { name })).toBeInTheDocument();
    }
  });

  it("keeps the footer wrapper from taking a full screen on app pages", () => {
    // .sentry sets min-height: 100vh; without foot-shell the footer leaves a screen of blank space.
    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <App />
      </MemoryRouter>,
    );
    const footer = screen.getByRole("navigation", { name: "Footer" }).closest("footer");
    expect(footer?.parentElement).toHaveClass("sentry", "foot-shell");
  });
});
