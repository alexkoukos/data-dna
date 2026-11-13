import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OutcomeChip } from "./OutcomeChip";

describe("OutcomeChip", () => {
  it("always shows a text label, not only a color", () => {
    render(<OutcomeChip outcome="local" detail="data stayed inside" />);
    expect(screen.getByText("Answered locally")).toBeInTheDocument();
    expect(screen.getByText(/data stayed inside/)).toBeInTheDocument();
  });

  it("shows an icon next to every label", () => {
    const outcomes = ["allow", "mask", "warn", "local", "block"] as const;
    for (const outcome of outcomes) {
      const { container, unmount } = render(<OutcomeChip outcome={outcome} />);
      expect(container.querySelector("svg")).not.toBeNull();
      unmount();
    }
  });
});
