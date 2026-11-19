import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatPage from "./ChatPage";

afterEach(() => vi.unstubAllGlobals());

const json = (b: unknown, status = 200, h: Record<string, string> = {}) =>
  new Response(JSON.stringify(b), {
    status,
    headers: { "Content-Type": "application/json", ...h },
  });
const gatewayError = (type: "warn" | "block") =>
  json(
    {
      error: {
        code: type === "warn" ? "409" : "403",
        provider_specific_fields: { type, reasons: ["Contains iban"], suggested_rewrite: null },
      },
    },
    type === "warn" ? 409 : 403,
  );

/** The gate stops the first send; a send with X-DNA-Reroute gets an answer from Company AI. */
function stubGateway(stop: "warn" | "block") {
  const chats: Record<string, string>[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/v1/keys")) return json({ key: "sk-test", default_model: "demo-mock" });
      if (url.includes("tool-request-outcomes")) return json([]);
      const headers = (init?.headers ?? {}) as Record<string, string>;
      chats.push(headers);
      if (headers["X-DNA-Reroute"] === "1") {
        return json({ choices: [{ message: { content: "Here is a safe answer." } }] }, 200, {
          "x-dna-decision": "rerouted",
          "x-dna-reasons": "",
        });
      }
      return gatewayError(stop);
    }),
  );
  return chats;
}

async function sendRisky() {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <ChatPage />
    </MemoryRouter>,
  );
  await user.type(await screen.findByLabelText("Your question"), "Pay GR1601101250000000012300695");
  await user.click(screen.getByRole("button", { name: /send/i }));
  return user;
}

describe("Send it to Company AI instead", () => {
  it("is offered on a block, and the answer is marked as from Company AI", async () => {
    const chats = stubGateway("block");
    const user = await sendRisky();
    await user.click(await screen.findByRole("button", { name: "Send it to Company AI instead" }));
    expect(await screen.findByText("Answered by Company AI")).toBeInTheDocument();
    expect(screen.getByText("Here is a safe answer.")).toBeInTheDocument();
    expect(chats.map((h) => h["X-DNA-Reroute"])).toEqual([undefined, "1"]);
    // the message now shows the new outcome, not "Blocked"
    expect(screen.getAllByText("Sent to Company AI").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Send it to Company AI instead" })).toBeNull();
  });

  it("is offered on a warning too, next to Send anyway", async () => {
    const chats = stubGateway("warn");
    const user = await sendRisky();
    expect(await screen.findByRole("button", { name: "Send anyway" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Send it to Company AI instead" }));
    expect(await screen.findByText("Answered by Company AI")).toBeInTheDocument();
    expect(chats[1]["X-DNA-Reroute"]).toBe("1");
    expect(chats[1]["X-DNA-Ack"]).toBeUndefined(); // rerouting is not "send anyway"
  });

  it("is not offered when nothing was stopped", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).includes("/v1/keys")
          ? json({ key: "k", default_model: "m" })
          : json({ choices: [{ message: { content: "Hi" } }] }),
      ),
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    );
    await user.type(await screen.findByLabelText("Your question"), "hello");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByText("Hi");
    expect(screen.queryByRole("button", { name: "Send it to Company AI instead" })).toBeNull();
  });
});
