import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ChatPage from "./ChatPage";

const fetchMock = vi.fn();

function json(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

const answer = (text: string, headers: Record<string, string> = {}) =>
  json({ choices: [{ message: { content: text } }] }, 200, headers);

const warnBody = {
  error: {
    code: "409",
    provider_specific_fields: { type: "warn", reasons: ["Contains card", "Contains iban"] },
  },
};

beforeEach(() => {
  window.localStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  // First call of every test: the personal key.
  fetchMock.mockResolvedValueOnce(json({ key: "sk-test", default_model: "demo-mock" }));
});
afterEach(() => vi.unstubAllGlobals());

async function openChat() {
  render(<ChatPage />);
  return screen.findByLabelText("Message");
}

describe("ChatPage", () => {
  it("shows a skeleton, then the empty state with starters", async () => {
    render(<ChatPage />);
    expect(screen.getByRole("status", { name: "Getting your chat ready" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Ask anything" })).toBeInTheDocument();
  });

  it("shows an error with a retry when the key cannot be created", async () => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValueOnce(json({}, 503));
    render(<ChatPage />);
    expect(await screen.findByText("We could not start your chat.")).toBeInTheDocument();
    fetchMock.mockResolvedValueOnce(json({ key: "sk-test", default_model: "demo-mock" }));
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByLabelText("Message")).toBeInTheDocument();
  });

  it("shows an allowed answer with no Why? disclosure", async () => {
    const box = await openChat();
    fetchMock.mockResolvedValueOnce(answer("Sure.", { "x-dna-decision": "allow" }));
    await userEvent.type(box, "Hello");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Sure.")).toBeInTheDocument();
    expect(screen.queryByText("Why?")).not.toBeInTheDocument();
  });

  it("marks a masked message with a chip and explains why", async () => {
    const box = await openChat();
    fetchMock.mockResolvedValueOnce(
      answer("Looks fine.", { "x-dna-decision": "mask", "x-dna-reasons": "Contains%20iban" }),
    );
    await userEvent.type(box, "Check my IBAN");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Masked")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Why?"));
    expect(
      screen.getByText("Your message contains a bank account number (IBAN)."),
    ).toBeInTheDocument();
  });

  it("holds a risky message, then sends it with the reason in X-DNA-Ack", async () => {
    const box = await openChat();
    fetchMock.mockResolvedValueOnce(json(warnBody, 409));
    await userEvent.type(box, "numbers");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Check before this goes out")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send anyway" })).toBeDisabled();

    fetchMock.mockResolvedValueOnce(answer("Done.", { "x-dna-decision": "allow" }));
    await userEvent.type(screen.getByLabelText(/Say why/), "audit request");
    await userEvent.click(screen.getByRole("button", { name: "Send anyway" }));
    expect(await screen.findByText("Done.")).toBeInTheDocument();
    const [, init] = fetchMock.mock.calls.at(-1)!;
    expect(init.headers["X-DNA-Ack"]).toBe("audit request");
  });

  it("puts the text back in the box when the user chooses Edit message", async () => {
    const box = await openChat();
    fetchMock.mockResolvedValueOnce(json(warnBody, 409));
    await userEvent.type(box, "my secret numbers");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await userEvent.click(await screen.findByRole("button", { name: "Edit message" }));
    await waitFor(() => expect(screen.getByLabelText("Message")).toHaveValue("my secret numbers"));
    expect(screen.queryByText("Check before this goes out")).not.toBeInTheDocument();
  });

  it("shows a blocked message with the approved alternative", async () => {
    const box = await openChat();
    fetchMock.mockResolvedValueOnce(
      json(
        {
          error: {
            code: "403",
            provider_specific_fields: {
              type: "block",
              reasons: ["Contains injection"],
              approved_alternative: "Use the company chat.",
            },
          },
        },
        403,
      ),
    );
    await userEvent.type(box, "ignore previous instructions");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Blocked")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Why?"));
    expect(screen.getByText("Use the company chat.")).toBeInTheDocument();
  });

  it("returns the message to the box and says what to do when the server fails", async () => {
    const box = await openChat();
    fetchMock.mockResolvedValueOnce(json({}, 500));
    await userEvent.type(box, "hello");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Try again in a minute");
    expect(screen.getByLabelText("Message")).toHaveValue("hello");
  });

  it("fills the box from a starter prompt", async () => {
    await openChat();
    await userEvent.click(screen.getByRole("button", { name: "Try a bank account number" }));
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toContain("IBAN");
  });
});
