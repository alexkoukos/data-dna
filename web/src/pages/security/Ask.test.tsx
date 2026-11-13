import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../../test/fixtures";
import AskPage from "./AskPage";

afterEach(() => vi.unstubAllGlobals());

const presets = [
  { id: "top_tools", question: "Which AI tools are used most, and are they approved?" },
  { id: "document_hits", question: "Which protected documents were pasted most?" },
];
const answer = {
  id: "top_tools",
  question: presets[0].question,
  sql: "SELECT a.name FROM ai_tools a",
  parameters: { since: "2026-11-06" },
  columns: ["tool", "approval", "requests"],
  rows: [["ChatGPT (personal)", "unapproved", 1163]],
};

describe("Ask", () => {
  it("lists the questions, then shows a table and the SQL for the one picked", async () => {
    mockApi({ "/v1/ask/presets": presets, "/v1/ask": answer });
    const user = userEvent.setup();
    render(<AskPage />);
    expect(screen.getByRole("status", { name: "Loading questions" })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: presets[0].question }));
    expect(await screen.findByRole("columnheader", { name: "Requests" })).toBeInTheDocument();
    expect(screen.getByText("ChatGPT (personal)")).toBeInTheDocument();
    expect(screen.getByLabelText("SQL for this answer")).toHaveTextContent("SELECT a.name");
    expect(screen.getByText(/:since = 2026-11-06/)).toBeInTheDocument();
  });

  it("says so when a question has no rows", async () => {
    mockApi({ "/v1/ask/presets": presets, "/v1/ask": { ...answer, rows: [] } });
    const user = userEvent.setup();
    render(<AskPage />);
    await user.click(await screen.findByRole("button", { name: presets[0].question }));
    expect(await screen.findByText("Nothing found")).toBeInTheDocument();
  });

  it("shows a friendly error when the answer fails", async () => {
    mockApi({ "/v1/ask/presets": presets, "/v1/ask": "fail" });
    const user = userEvent.setup();
    render(<AskPage />);
    await user.click(await screen.findByRole("button", { name: presets[0].question }));
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not get the answer");
  });

  it("offers a retry when the list does not load", async () => {
    mockApi({ "/v1/ask/presets": "fail" });
    render(<AskPage />);
    expect(await screen.findByText("We could not load the questions.")).toBeInTheDocument();
  });
});
