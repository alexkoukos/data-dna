import { MemoryRouter } from "react-router-dom";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../test/fixtures";
import { RequestToolForm } from "../components/RequestToolForm";
import { outcomeText, type ToolRequest } from "../lib/toolRequestsApi";
import RequestsTab from "./security/RequestsTab";
import ChatPage from "./ChatPage";

afterEach(() => vi.unstubAllGlobals());

const pending: ToolRequest = {
  id: 4,
  created_at: "now",
  requester: "maria",
  team: "Finance",
  tool: "Perplexity",
  reason: "Needs live web search",
  status: "pending",
  decided_by: null,
  note: null,
  risk: null,
  allowed_categories: null,
  alternative: null,
};
const bodyOf = (fn: ReturnType<typeof mockApi>, part: string): unknown => {
  const call = (fn.mock.calls as unknown[][]).find(([u]) => String(u).includes(part));
  return JSON.parse(String((call?.[1] as { body?: string } | undefined)?.body ?? "null"));
};

describe("Request an AI tool", () => {
  it("sends the tool and reason, with the user from the key", async () => {
    const fn = mockApi({ "/v1/tool-requests": pending });
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <RequestToolForm userId="maria" team="Finance" initialTool="Perplexity" onClose={onClose} />,
    );
    const send = screen.getByRole("button", { name: "Send request" });
    expect(send).toBeDisabled();
    await user.type(screen.getByLabelText("Why do you need it?"), "Needs live web search");
    await user.click(send);
    expect(await screen.findByText("Request sent.")).toBeInTheDocument();
    expect(bodyOf(fn, "/v1/tool-requests")).toEqual({
      user_id: "maria",
      team: "Finance",
      tool: "Perplexity",
      reason: "Needs live web search",
    });
  });

  it("shows the server's reason when the request is refused", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "Perplexity is already approved." }), {
            status: 409,
          }),
      ),
    );
    const user = userEvent.setup();
    render(
      <RequestToolForm userId="u" team="t" initialTool="Perplexity" onClose={() => undefined} />,
    );
    await user.type(screen.getByLabelText("Why do you need it?"), "x");
    await user.click(screen.getByRole("button", { name: "Send request" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already approved");
  });

  it("is offered from the chat page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () => new Response(JSON.stringify({ key: "sk-test", default_model: "demo-mock" })),
      ),
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    );
    await user.click(await screen.findByRole("button", { name: "Request approval" }));
    expect(screen.getByRole("form", { name: "Request an AI tool" })).toBeInTheDocument();
  });
});

describe("Outcome on the next message", () => {
  it("shows the decision once, when the person sends their next message", async () => {
    const ok = (b: unknown, h: Record<string, string> = {}) =>
      new Response(JSON.stringify(b), {
        status: 200,
        headers: { "Content-Type": "application/json", ...h },
      });
    let collected = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("tool-request-outcomes")) {
          return ok(
            collected++ === 0
              ? [{ ...pending, status: "approved", risk: "low", allowed_categories: [] }]
              : [],
          );
        }
        if (url.includes("/v1/keys")) return ok({ key: "sk-test", default_model: "demo-mock" });
        return ok({ choices: [{ message: { content: "Hi" } }] });
      }),
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    );
    await user.type(await screen.findByLabelText("Your question"), "hello");
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByText(/Perplexity was approved \(risk: low\)/)).toBeInTheDocument();
  });
});

describe("Requests tab", () => {
  it("approves with risk, allowed data and the reviewer's name", async () => {
    const fn = mockApi({ "/decision": pending, "/v1/tool-requests": [pending] });
    const user = userEvent.setup();
    render(<RequestsTab onChanged={() => undefined} />);
    expect(await screen.findByText("Needs live web search")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    await user.type(screen.getByLabelText(/Your name/), "sec1");
    await user.selectOptions(screen.getByLabelText("Risk rating"), "low");
    await user.click(screen.getByLabelText("iban"));
    await user.click(screen.getByRole("button", { name: "Approve" }));
    expect(await screen.findByText("Perplexity is now approved.")).toBeInTheDocument();
    expect(bodyOf(fn, "/4/decision")).toEqual({
      reviewer: "sec1",
      approve: true,
      risk: "low",
      allowed_categories: ["iban"],
      alternative: "Company AI",
      note: "",
    });
  });

  it("lists decided requests apart from waiting ones", async () => {
    mockApi({
      "/v1/tool-requests": [
        pending,
        { ...pending, id: 5, tool: "Claude", status: "approved", decided_by: "sec1" },
      ],
    });
    render(<RequestsTab onChanged={() => undefined} />);
    expect(await screen.findByRole("heading", { name: "Waiting (1)" })).toBeInTheDocument();
    const decided = screen.getByRole("heading", { name: "Decided" })
      .nextElementSibling as HTMLElement;
    expect(within(decided).getByText(/approved by sec1/)).toBeInTheDocument();
  });
});

describe("Outcome text", () => {
  it("says approved with the risk and allowed data", () => {
    const t = outcomeText({
      ...pending,
      status: "approved",
      risk: "low",
      allowed_categories: ["iban"],
    });
    expect(t).toBe("Perplexity was approved (risk: low). You can use it with: iban.");
  });
  it("says rejected with the note and the alternative", () => {
    const t = outcomeText({
      ...pending,
      status: "rejected",
      note: "Keeps prompts.",
      alternative: "Company AI",
    });
    expect(t).toBe("Perplexity was not approved. Keeps prompts. Use Company AI instead.");
  });
});
