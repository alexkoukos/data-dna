import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WarnCard } from "./WarnCard";

const base = {
  reasons: ["Contains client name"],
  onEdit: vi.fn(),
  onSendAnyway: vi.fn(),
  onCancel: vi.fn(),
};

describe("WarnCard coaching (X19)", () => {
  it("offers the safer version as the primary action when there is one", async () => {
    const onUse = vi.fn();
    render(<WarnCard {...base} suggestion="Draft a note to [CLIENT_1]" onUseSuggestion={onUse} />);
    expect(screen.getByLabelText("Safer version")).toHaveTextContent("[CLIENT_1]");
    await userEvent.click(screen.getByRole("button", { name: "Send the safer version" }));
    expect(onUse).toHaveBeenCalledOnce();
  });
  it("keeps Edit message as the primary action without a suggestion", () => {
    render(<WarnCard {...base} />);
    expect(screen.queryByRole("button", { name: "Send the safer version" })).toBeNull();
    expect(screen.getByRole("button", { name: "Edit message" })).toBeInTheDocument();
  });
});
