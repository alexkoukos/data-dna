import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../../test/fixtures";
import DocumentsPage from "./DocumentsPage";

afterEach(() => vi.unstubAllGlobals());

const docs = [
  {
    id: 1,
    title: "Merger memo",
    sensitivity: "restricted",
    dna_enabled: false,
    created_at: null,
    incidents: 0,
  },
];
const marks = Array.from({ length: 6 }, (_, i) => ({
  position: i,
  variants: [`a${i}`, `b${i}`, `c${i}`, `d${i}`],
  preview: `ref. a${i}`,
}));

describe("Documents: adding and marks", () => {
  it("adds a pasted document and says what was stored", async () => {
    const fetchMock = mockApi({
      "/dna": { enabled: false, marks: 0, copies: [] },
      "/v1/documents": (_url: string) => docs,
    });
    const user = userEvent.setup();
    render(<DocumentsPage />);
    await screen.findByText("Merger memo");
    await user.click(screen.getByText("Add a document"));
    const add = screen.getByRole("button", { name: "Add the document" });
    expect(add).toBeDisabled();
    await user.type(screen.getByLabelText("Title"), "Tender");
    await user.type(screen.getByLabelText("Or paste the text"), "some confidential words here");
    expect(add).toBeEnabled();
    fetchMock.mockImplementationOnce(
      async () =>
        new Response(
          JSON.stringify({ id: 2, title: "Tender", sensitivity: "confidential", chunks: 3 }),
        ),
    );
    await user.click(add);
    expect(await screen.findByText(/Added "Tender" \(3 parts\)/)).toBeInTheDocument();
  });

  it("proposes marks, then approves them", async () => {
    mockApi({
      "/dna/propose": { marks },
      "/dna/approve": { enabled: true, marks: 6, copies: [] },
      "/dna": { enabled: false, marks: 0, copies: [] },
      "/v1/documents": docs,
    });
    const user = userEvent.setup();
    render(<DocumentsPage />);
    await user.click(await screen.findByRole("button", { name: "Suggest marks" }));
    expect(await screen.findByText(/After sentence 1:/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Approve these 6 marks" }));
  });

  it("issues copies and links to each one", async () => {
    mockApi({
      "/copies": [{ copy_code: "7F3A", recipient: "u-ann" }],
      "/dna": { enabled: true, marks: 6, copies: [] },
      "/v1/documents": docs,
    });
    const user = userEvent.setup();
    render(<DocumentsPage />);
    await screen.findByText(/6 marks approved/);
    await user.type(screen.getByLabelText(/Who gets a copy/), "u-ann");
    await user.click(screen.getByRole("button", { name: "Issue copies" }));
    expect(await screen.findByText("7F3A")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open copy 7F3A" })).toHaveAttribute(
      "href",
      "/api/v1/documents/1/copies/7F3A",
    );
  });

  it("shows the server's plain refusal", async () => {
    mockApi({ "/dna": { enabled: true, marks: 6, copies: [] }, "/v1/documents": docs });
    const user = userEvent.setup();
    render(<DocumentsPage />);
    await user.type(await screen.findByLabelText(/Who gets a copy/), "u-nobody");
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "Unknown recipient: u-nobody." }), { status: 422 }),
      ),
    );
    await user.click(screen.getByRole("button", { name: "Issue copies" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unknown recipient: u-nobody.");
  });
});
