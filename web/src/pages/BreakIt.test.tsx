import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../test/fixtures";
import BreakItPage from "./BreakItPage";

afterEach(() => vi.unstubAllGlobals());

const layers = [
  {
    id: "normalise",
    level: 1,
    label: "Cleaning of tricks",
    fired: true,
    detail: "spaced_characters",
  },
  { id: "identifiers", level: 2, label: "Identifiers and checksums", fired: true, detail: "IBAN" },
  { id: "injection", level: 3, label: "Prompt injection", fired: false, detail: "" },
];
const caught = {
  decision: "warn",
  reasons: ["Contains iban", "Evasion attempt detected: spaced_characters"],
  masked_text: "Pay [IBAN_1]",
  evasion_signals: ["spaced_characters"],
  layers,
  caught_by: "Identifiers and checksums",
};
const examples = [{ category: "spacing", text: "G R 1 6" }];

describe("Try to break it", () => {
  it("shows the outcome, the reasons and what each level saw", async () => {
    mockApi({ "/v1/try/examples": examples, "/v1/try": caught });
    const user = userEvent.setup();
    render(<BreakItPage />);
    await user.type(screen.getByLabelText("Text to check"), "Pay G R 1 6");
    await user.click(screen.getByRole("button", { name: "Check it" }));
    const result = await screen.findByRole("region", { name: "Result" });
    expect(within(result).getByText("Warned")).toBeInTheDocument();
    expect(within(result).getByText("Stopped by: Identifiers and checksums")).toBeInTheDocument();
    expect(within(result).getByText("Contains iban")).toBeInTheDocument();
    const items = within(result).getAllByRole("listitem");
    expect(items.filter((i) => /Found something/.test(i.textContent ?? ""))).toHaveLength(2);
    expect(items.filter((i) => /Nothing found/.test(i.textContent ?? ""))).toHaveLength(1);
  });

  it("says plainly when nothing caught the text, and what to do", async () => {
    mockApi({
      "/v1/try/examples": [],
      "/v1/try": {
        ...caught,
        decision: "allow",
        reasons: [],
        caught_by: null,
        layers: layers.map((l) => ({ ...l, fired: false })),
      },
    });
    const user = userEvent.setup();
    render(<BreakItPage />);
    await user.type(screen.getByLabelText("Text to check"), "hello");
    await user.click(screen.getByRole("button", { name: "Check it" }));
    expect(await screen.findByText("Nothing caught this text")).toBeInTheDocument();
    expect(screen.getByText(/you found a gap/)).toBeInTheDocument();
  });

  it("shows the masked text when the outcome is a mask", async () => {
    mockApi({ "/v1/try/examples": [], "/v1/try": { ...caught, decision: "mask" } });
    const user = userEvent.setup();
    render(<BreakItPage />);
    await user.type(screen.getByLabelText("Text to check"), "Pay somewhere");
    await user.click(screen.getByRole("button", { name: "Check it" }));
    expect(await screen.findByLabelText("Masked text")).toHaveTextContent("Pay [IBAN_1]");
  });

  it("fills the box from an example and keeps the button off while it is empty", async () => {
    mockApi({ "/v1/try/examples": examples, "/v1/try": caught });
    const user = userEvent.setup();
    render(<BreakItPage />);
    expect(screen.getByRole("button", { name: "Check it" })).toBeDisabled();
    await user.click(await screen.findByRole("button", { name: "Spaced out" }));
    expect(screen.getByLabelText("Text to check")).toHaveValue("G R 1 6");
    expect(screen.getByRole("button", { name: "Check it" })).toBeEnabled();
  });

  it("tells the person what happened and what to do when the check fails", async () => {
    mockApi({ "/v1/try/examples": [], "/v1/try": "fail" });
    const user = userEvent.setup();
    render(<BreakItPage />);
    await user.type(screen.getByLabelText("Text to check"), "anything");
    await user.click(screen.getByRole("button", { name: "Check it" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("We could not check that text");
    expect(alert).toHaveTextContent("Your text is still in the box");
    expect(screen.getByLabelText("Text to check")).toHaveValue("anything");
  });
});
