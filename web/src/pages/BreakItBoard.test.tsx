import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../test/fixtures";
import BreakItPage from "./BreakItPage";
import ReviewPage from "./security/ReviewPage";

afterEach(() => vi.unstubAllGlobals());

const passed = {
  decision: "allow",
  reasons: [],
  masked_text: "hello",
  evasion_signals: [],
  layers: [],
  caught_by: null,
  attempt_id: "a1",
};
const bodyOf = (fn: ReturnType<typeof mockApi>, urlPart: string): unknown => {
  const call = (fn.mock.calls as unknown[][]).find(([u]) => String(u).includes(urlPart));
  return JSON.parse(String((call?.[1] as { body?: string } | undefined)?.body ?? "null"));
};
const board = {
  attempts: 4,
  stopped: 3,
  got_through: 1,
  catch_rate: 75,
  misses: [{ id: "a1", kind: "spacing", preview: "[masked preview]", nickname: null, at: "now" }],
  top_breakers: [{ nickname: "Eleni", submitted: 2, approved: 1 }],
};

describe("Break it leaderboard and 'It got through'", () => {
  it("shows today's counts, the misses by preview and kind, and the top breakers", async () => {
    mockApi({ "/v1/try/examples": [], "/v1/breakit/board": board });
    render(<BreakItPage />);
    const lb = await screen.findByRole("region", { name: "Leaderboard" });
    expect(within(lb).getByText("75%")).toBeInTheDocument();
    expect(within(lb).getByText("[masked preview]")).toBeInTheDocument();
    expect(within(lb).getByText("Eleni")).toBeInTheDocument();
    expect(within(lb).getByText("1 approved, 2 sent")).toBeInTheDocument();
  });

  it("sends the checked text, the expected decision and the kind, and says what is kept", async () => {
    const fn = mockApi({
      "/v1/try/examples": [],
      "/v1/breakit/board": board,
      "/v1/breakit/candidates": {},
      "/v1/try": passed,
    });
    const user = userEvent.setup();
    render(<BreakItPage />);
    await user.type(screen.getByLabelText("Text to check"), "hello");
    await user.click(screen.getByRole("button", { name: "Check it" }));
    await user.click(await screen.findByRole("button", { name: "It got through" }));
    expect(screen.getByText(/saves the exact text you typed/)).toBeInTheDocument();
    await user.click(screen.getByLabelText("Block it"));
    await user.selectOptions(screen.getByLabelText("Kind of trick"), "greeklish");
    await user.click(screen.getByRole("button", { name: "Send this text as a test case" }));
    expect(await screen.findByText(/review it before it joins/)).toBeInTheDocument();
    expect(bodyOf(fn, "/v1/breakit/candidates")).toEqual({
      text: "hello",
      expected_decision: "block",
      kind: "greeklish",
      nickname: null,
    });
  });

  it("offers no 'It got through' button when the gate stopped the text", async () => {
    mockApi({
      "/v1/try/examples": [],
      "/v1/breakit/board": board,
      "/v1/try": { ...passed, decision: "block", caught_by: "x", reasons: ["r"] },
    });
    const user = userEvent.setup();
    render(<BreakItPage />);
    await user.type(screen.getByLabelText("Text to check"), "hello");
    await user.click(screen.getByRole("button", { name: "Check it" }));
    await screen.findByRole("region", { name: "Result" });
    expect(screen.queryByRole("button", { name: "It got through" })).toBeNull();
  });
});

describe("Break it review queue", () => {
  const queue = [
    {
      id: 7,
      created_at: "now",
      nickname: "Eleni",
      kind: "spacing",
      expected_decision: "warn",
      got_decision: "allow",
      text: "the submitted text",
      preview: "p",
    },
  ];

  it("approves with the reviewer's name and refreshes the queue", async () => {
    let calls = 0;
    const fn = mockApi({
      "/approve": { status: "approved", eval_id: "BI001" },
      "/v1/breakit/candidates": () => (calls++ === 0 ? queue : []),
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ReviewPage />
      </MemoryRouter>,
    );
    expect(await screen.findByLabelText("Submitted text")).toHaveTextContent("the submitted text");
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    await user.type(screen.getByLabelText(/Your name/), "sec1");
    await user.click(screen.getByRole("button", { name: "Approve" }));
    expect(await screen.findByText(/now a row in the test set/)).toBeInTheDocument();
    expect(await screen.findByText("Nothing to review")).toBeInTheDocument();
    expect(bodyOf(fn, "/7/approve")).toEqual({ reviewer: "sec1" });
  });

  it("rejects and says the text was deleted", async () => {
    mockApi({ "/reject": { status: "rejected" }, "/v1/breakit/candidates": queue });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ReviewPage />
      </MemoryRouter>,
    );
    await screen.findByLabelText("Submitted text");
    await user.type(screen.getByLabelText(/Your name/), "sec1");
    await user.click(screen.getByRole("button", { name: "Reject and delete" }));
    expect(await screen.findByText(/The text was deleted/)).toBeInTheDocument();
  });
});
