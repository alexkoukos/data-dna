import { render, screen } from "@testing-library/react";
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
    expect(screen.getByRole("link", { name: "Company Chat" })).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("shows a way back for an unknown address instead of a blank page", () => {
    render(
      <MemoryRouter initialEntries={["/no-such-page"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "This page does not exist" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to the home page" })).toHaveAttribute(
      "href",
      "/app",
    );
  });
});
