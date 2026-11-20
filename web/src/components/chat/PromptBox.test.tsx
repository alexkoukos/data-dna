import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Attachment } from "../../lib/attachments";
import { PromptBox } from "./PromptBox";

const ready: Attachment = {
  id: "1",
  status: "ready",
  name: "report.pdf",
  text: "Quarterly figures",
  chars: 17,
  truncated: false,
};

function box(props: Partial<Parameters<typeof PromptBox>[0]> = {}) {
  const handlers = { onSend: vi.fn(), onAddFiles: vi.fn(), onRemoveFile: vi.fn() };
  render(<PromptBox value="" onChange={() => undefined} busy={false} {...handlers} {...props} />);
  return handlers;
}

describe("PromptBox attachments", () => {
  it("has a labelled attach button that opens a picker for the accepted types", async () => {
    const { onAddFiles } = box();
    const button = screen.getByRole("button", { name: "Attach files" });
    expect(button).toBeInTheDocument();
    const input = document.querySelector<HTMLInputElement>('input[type="file"]')!;
    expect(input.accept).toBe(".pdf,.docx,.txt,.md,.csv");
    const file = new File(["hello"], "notes.txt", { type: "text/plain" });
    await userEvent.upload(input, file);
    expect(onAddFiles).toHaveBeenCalledWith([file]);
  });

  it("shows each file's state in words and removes a file", async () => {
    const { onRemoveFile } = box({
      attachments: [
        ready,
        { id: "2", status: "reading", name: "memo.docx" },
        { ...ready, id: "3", name: "long.txt", truncated: true, chars: 90_000 },
        { id: "4", status: "error", name: "photo.png", message: "photo.png was not added." },
      ],
    });
    expect(screen.getByText("· Ready")).toBeInTheDocument();
    expect(screen.getByText("· Checking…")).toBeInTheDocument();
    expect(screen.getByText("· Shortened")).toBeInTheDocument();
    expect(screen.getByText(/only the first 30,000 characters/)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("photo.png was not added.");
    await userEvent.click(screen.getByRole("button", { name: "Remove memo.docx" }));
    expect(onRemoveFile).toHaveBeenCalledWith("2");
  });

  it("can send a file with no typed text", async () => {
    const { onSend } = box({ attachments: [ready] });
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(onSend).toHaveBeenCalledOnce();
  });

  it("waits until every file has been checked before sending", () => {
    box({ value: "Summarise", attachments: [{ id: "2", status: "reading", name: "a.pdf" }] });
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("does not send when only a failed file is attached", () => {
    box({
      attachments: [{ id: "4", status: "error", name: "x.exe", message: "x.exe was not added." }],
    });
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });
});
