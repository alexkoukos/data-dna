import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../../test/fixtures";
import DocumentsPage from "./DocumentsPage";
import PoliciesPage from "./PoliciesPage";

afterEach(() => vi.unstubAllGlobals());

const policies = [
  { scope: "category", key: "card", action: "mask", updated_by: null, updated_at: null },
  { scope: "category", key: "client_name", action: "warn", updated_by: null, updated_at: null },
  { scope: "sensitivity", key: "restricted", action: "block", updated_by: null, updated_at: null },
];

describe("Policies", () => {
  it("shows a skeleton, then rows in plain words with today's effect", async () => {
    mockApi({ "/v1/policies": policies });
    render(<PoliciesPage />);
    expect(screen.getByRole("status", { name: "Loading policies" })).toBeInTheDocument();
    expect(await screen.findByText("Payment cards")).toBeInTheDocument();
    expect(screen.getByText("Restricted documents")).toBeInTheDocument();
    expect(screen.getByLabelText("What happens to payment cards")).toHaveValue("mask");
    expect(screen.getAllByText(/^Today:/)).toHaveLength(3);
  });

  it("previews the effect and saves only when asked", async () => {
    const fetchMock = mockApi({
      "/v1/policies": (_url: string) => policies,
    });
    const user = userEvent.setup();
    render(<PoliciesPage />);
    const select = await screen.findByLabelText("What happens to payment cards");
    await user.selectOptions(select, "block");
    expect(screen.getByText(/If you save:.*not sent/)).toBeInTheDocument();
    // Nothing was sent yet.
    expect(fetchMock).toHaveBeenCalledTimes(1); // only the load
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ ...policies[0], action: "block", updated_by: "dashboard" }),
            {
              status: 200,
            },
          ),
      ),
    );
    await user.click(screen.getByRole("button", { name: "Save payment cards" }));
    expect(await screen.findAllByText(/^Today:.*not sent/)).toHaveLength(2);
    expect(select).toHaveValue("block");
    expect(screen.queryByRole("button", { name: "Save payment cards" })).not.toBeInTheDocument();
  });

  it("cancel puts the old choice back", async () => {
    mockApi({ "/v1/policies": policies });
    const user = userEvent.setup();
    render(<PoliciesPage />);
    const select = await screen.findByLabelText("What happens to payment cards");
    await user.selectOptions(select, "allow");
    expect(screen.getByText("Nothing will be checked for this any more.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(select).toHaveValue("mask");
  });

  it("says nothing was changed when saving fails", async () => {
    mockApi({ "/v1/policies": policies });
    const user = userEvent.setup();
    render(<PoliciesPage />);
    await user.selectOptions(await screen.findByLabelText("What happens to payment cards"), "warn");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status: 500 })),
    );
    await user.click(screen.getByRole("button", { name: "Save payment cards" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Nothing was changed");
  });

  it("offers a retry when loading fails", async () => {
    mockApi({ "/v1/policies": "fail" });
    render(<PoliciesPage />);
    expect(await screen.findByText("We could not load the policies.")).toBeInTheDocument();
  });
});

describe("Documents", () => {
  it("lists documents with sensitivity and incident counts", async () => {
    mockApi({
      "/v1/documents": [
        {
          id: 1,
          title: "Merger memo",
          sensitivity: "restricted",
          dna_enabled: false,
          created_at: "2026-11-01T10:00:00Z",
          incidents: 4,
        },
      ],
    });
    render(<DocumentsPage />);
    expect(await screen.findByText("Merger memo")).toBeInTheDocument();
    expect(screen.getByText("Restricted")).toBeInTheDocument();
    expect(screen.getByText("Not set up yet")).toBeInTheDocument();
    expect(screen.getByText("2026-11-01")).toBeInTheDocument();
  });

  it("explains the empty state", async () => {
    mockApi({ "/v1/documents": [] });
    render(<DocumentsPage />);
    expect(await screen.findByText("No protected documents yet")).toBeInTheDocument();
  });
});
