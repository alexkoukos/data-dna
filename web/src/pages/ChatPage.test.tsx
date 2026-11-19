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

describe("Company AI chat with files", () => {
  const extracted = (text: string, truncated = false) =>
    new Response(
      JSON.stringify({ filename: "x", kind: "pdf", text, chars: text.length, truncated }),
    );

  function stubServer(decision = "mask") {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        calls.push({ url, body: init?.body });
        if (url.includes("/keys"))
          return new Response(JSON.stringify({ key: "k", default_model: "m" }));
        if (url.includes("/files/limits"))
          return new Response(
            JSON.stringify({
              max_bytes: 1000,
              max_files: 2,
              max_chars: 30000,
              types: [".csv", ".docx", ".md", ".pdf", ".txt"],
            }),
          );
        if (url.includes("/files/extract")) {
          const file = (init?.body as FormData).get("file") as File;
          if (file.name === "scan.pdf")
            return new Response(
              JSON.stringify({
                detail: { filename: "scan.pdf", message: "No text was found in this PDF." },
              }),
              { status: 422 },
            );
          return extracted(`Pay GR1601101250000000012300695 (${file.name})`);
        }
        return new Response(JSON.stringify({ choices: [{ message: { content: "Done." } }] }), {
          headers: { "x-dna-decision": decision, "x-dna-reasons": "iban" },
        });
      }),
    );
    return calls;
  }

  const fileInput = () => document.querySelector<HTMLInputElement>('input[type="file"]')!;
  const pdf = (name = "report.pdf", size = 10) =>
    new File(["%PDF-".padEnd(size, "x")], name, { type: "application/pdf" });

  it("sends the file text inside the message and shows the outcome with the file name", async () => {
    const calls = stubServer("mask");
    render(<ChatPage />);
    await userEvent.upload(fileInput(), pdf());
    expect(await screen.findByText("· Ready")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox", { name: "Your question" }), "Summarise it");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Done.")).toBeInTheDocument();
    const sent = calls.find((c) => c.url.includes("/chat/completions"))!;
    const message = (JSON.parse(String(sent.body)) as { messages: { content: string }[] })
      .messages[0]!.content;
    expect(message).toContain("Summarise it\n\n[File: report.pdf]\n");
    expect(message).toContain("[End of file: report.pdf]");
    expect(screen.getByText("· report.pdf")).toBeInTheDocument(); // on the outcome chip
    expect(screen.getByText("Masked")).toBeInTheDocument();
    // The chips are cleared after sending, and the file text never reaches localStorage.
    expect(screen.queryByRole("button", { name: "Remove report.pdf" })).not.toBeInTheDocument();
    expect(localStorage.getItem("sentry.chats")).toContain("report.pdf");
    expect(localStorage.getItem("sentry.chats")).not.toContain("GR1601101250000000012300695");
  });

  it("explains files it cannot take, and keeps the limit on the number of files", async () => {
    stubServer();
    render(<ChatPage />);
    await screen.findByRole("button", { name: "Attach files" });
    await waitForLimits();
    await userEvent.upload(fileInput(), [pdf("scan.pdf"), pdf("big.pdf", 2000)]);
    expect(await screen.findByText(/No text was found in this PDF/)).toBeInTheDocument();
    expect(screen.getByText(/big.pdf is larger than 1 KB/)).toBeInTheDocument();
    await userEvent.upload(fileInput(), [pdf("a.pdf"), pdf("b.pdf"), pdf("c.pdf")]);
    expect(
      await screen.findByText(/c.pdf was not added. You can attach up to 2 files/),
    ).toBeInTheDocument();
    const exe = new File(["MZ"], "tool.exe");
    await userEvent.upload(fileInput(), exe, { applyAccept: false });
    expect(await screen.findByText(/tool.exe was not added. Attach a PDF/)).toBeInTheDocument();
  });

  it("shows the extension's hand-off banner and lets the person dismiss it", async () => {
    stubServer();
    window.history.pushState({}, "", "/chat?from=chatgpt&file=q4-report.pdf");
    render(<ChatPage />);
    const banner = screen.getByRole("region", { name: "Upload the file here instead" });
    expect(banner).toHaveTextContent("You tried to upload q4-report.pdf to ChatGPT.");
    expect(banner).toHaveTextContent("it is checked first and you will still get an answer");
    await userEvent.click(screen.getByRole("button", { name: "Dismiss this message" }));
    expect(screen.queryByRole("region", { name: "Upload the file here instead" })).toBeNull();
    expect(window.location.search).toBe("");
  });
});

async function waitForLimits() {
  // the limits request resolves on the next tick
  await new Promise((r) => setTimeout(r, 0));
}
