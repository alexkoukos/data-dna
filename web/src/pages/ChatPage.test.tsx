import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ChatPage from "./ChatPage";

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

const answerWith = (content: string, decision = "local") =>
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) =>
      url.includes("/keys")
        ? new Response(JSON.stringify({ key: "k", default_model: "m" }))
        : new Response(JSON.stringify({ choices: [{ message: { content } }] }), {
            headers: { "x-dna-decision": decision, "x-dna-reasons": "iban" },
          }),
    ),
  );

describe("Company AI chat", () => {
  it("starts with a prompt, starter categories and an empty history", () => {
    render(<ChatPage />);
    expect(screen.getByRole("heading", { name: "What can I help with?" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Your question" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Summarise" })).toBeInTheDocument();
    expect(screen.getByText(/appear here after the first question/i)).toBeInTheDocument();
  });

  it("suggests library prompts while typing and fills the input when one is chosen", async () => {
    render(<ChatPage />);
    await userEvent.type(screen.getByRole("textbox", { name: "Your question" }), "retention");
    // The matched words are highlighted in their own span, so click the text after them.
    await userEvent.click(await screen.findByText(/policy in two sentences/));
    expect(screen.getByRole("textbox", { name: "Your question" })).toHaveValue(
      "Summarise our data retention policy in two sentences",
    );
  });

  it("shows the answer with its actions, the outcome and a history entry", async () => {
    answerWith("Ninety days.");
    render(<ChatPage />);
    await userEvent.type(
      screen.getByRole("textbox", { name: "Your question" }),
      "How long do we keep data?",
    );
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Ninety days.")).toBeInTheDocument();
    for (const name of ["Retry", "Like", "Dislike", "Share"])
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    // Copy is on both the question and the answer.
    expect(screen.getAllByRole("button", { name: "Copy" })).toHaveLength(2);
    expect(screen.getByText("Answered locally")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "How long do we keep data?" })).toBeInTheDocument();
  });

  it("deletes a chat from the history", async () => {
    answerWith("Ninety days.");
    render(<ChatPage />);
    await userEvent.type(screen.getByRole("textbox", { name: "Your question" }), "Keep this?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("Ninety days.");
    await userEvent.click(screen.getByRole("button", { name: /More for Keep this\?/ }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Delete" }));
    expect(screen.queryByRole("button", { name: "Keep this?" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What can I help with?" })).toBeInTheDocument();
  });
  it("does not send a masked turn again, so the gateway never sees the raw text twice", async () => {
    const bodies: { messages: unknown[] }[] = [];
    let n = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (!url.includes("/chat/completions"))
          return new Response(JSON.stringify({ key: "k", default_model: "m" }));
        if (typeof init?.body === "string") bodies.push(JSON.parse(init.body));
        n += 1;
        return new Response(
          JSON.stringify({
            choices: [{ message: { content: n === 1 ? "Looks fine." : "Sure." } }],
          }),
          { headers: { "x-dna-decision": n === 1 ? "mask" : "allow" } },
        );
      }),
    );
    render(<ChatPage />);
    await userEvent.type(screen.getByRole("textbox", { name: "Your question" }), "Check my IBAN");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Looks fine.")).toBeInTheDocument();
    await userEvent.type(
      screen.getByRole("textbox", { name: "Your question" }),
      "And one more thing",
    );
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Sure.")).toBeInTheDocument();
    expect(bodies.at(-1)?.messages).toHaveLength(1);
  });
});
