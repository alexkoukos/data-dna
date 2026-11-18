import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatPage from "./ChatPage";

afterEach(() => vi.restoreAllMocks());

describe("Company AI chat", () => {
  it("offers starter questions and the input before anything is asked", () => {
    render(<ChatPage />);
    expect(screen.getByRole("heading", { name: "Company AI" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /data retention policy/i })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Your question" })).toBeInTheDocument();
  });

  it("shows the answer with its actions and the outcome", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        url.includes("/keys")
          ? new Response(JSON.stringify({ key: "k", default_model: "m" }))
          : new Response(JSON.stringify({ choices: [{ message: { content: "Ninety days." } }] }), {
              headers: { "x-dna-decision": "local" },
            }),
      ),
    );
    render(<ChatPage />);
    await userEvent.type(
      screen.getByRole("textbox", { name: "Your question" }),
      "How long do we keep data?",
    );
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Ninety days.")).toBeInTheDocument();
    for (const name of ["Retry", "Like", "Dislike", "Copy", "Share"])
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    expect(screen.getByText("Answered locally")).toBeInTheDocument();
  });
});
