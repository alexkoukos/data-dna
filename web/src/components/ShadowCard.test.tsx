import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ShadowCard } from "./ShadowCard";

describe("ShadowCard", () => {
  it("shows the switch state and asks to flip it", () => {
    const onToggle = vi.fn();
    render(
      <ShadowCard
        status={{ enabled: false, would_have: {}, total: 0 }}
        busy={false}
        error={null}
        onToggle={onToggle}
      />,
    );
    const sw = screen.getByRole("switch");
    expect(sw).toHaveAttribute("aria-checked", "false");
    fireEvent.click(sw);
    expect(onToggle).toHaveBeenCalledWith(true);
    expect(screen.getByText("Nothing recorded in shadow mode yet.")).toBeInTheDocument();
  });

  it("summarises what would have happened and shows errors", () => {
    render(
      <ShadowCard
        status={{ enabled: true, would_have: { block: 3, mask: 2 }, total: 5 }}
        busy={false}
        error="Shadow mode was not changed."
        onToggle={() => {}}
      />,
    );
    expect(
      screen.getByText(/Would have stopped or changed 5 messages: 3 blocked, 2 masked/),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("not changed");
  });
});
