import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OutcomeChip } from "./OutcomeChip";

describe("OutcomeChip", () => {
  it("always shows a text label, not only a color", () => {
    render(<OutcomeChip outcome="local" detail="data stayed inside" />);
    expect(screen.getByText("Answered locally")).toBeInTheDocument();
    expect(screen.getByText(/data stayed inside/)).toBeInTheDocument();
  });
});
