import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WhyPanel } from "./WhyPanel";

describe("WhyPanel", () => {
  it("lists each layer with its score and detail", () => {
    render(
      <WhyPanel
        trace={[
          {
            layer: "Document matching",
            fired: true,
            score: 0.93,
            detail: "paraphrase of a restricted document",
          },
          { layer: "Policy", fired: true, score: null, detail: "Decision: block" },
        ]}
      />,
    );
    expect(screen.getByText("Document matching")).toBeInTheDocument();
    expect(screen.getByText("score 93%")).toBeInTheDocument();
    expect(screen.getByText("Decision: block")).toBeInTheDocument();
  });

  it("says so when an old incident has no trace, and flags shadow mode", () => {
    const { rerender } = render(<WhyPanel trace={[]} />);
    expect(screen.getByText(/before the step-by-step explanation/)).toBeInTheDocument();
    rerender(
      <WhyPanel trace={[{ layer: "Policy", fired: true, score: null, detail: "x" }]} shadow />,
    );
    expect(screen.getByText(/Nothing was changed/)).toBeInTheDocument();
  });
});
