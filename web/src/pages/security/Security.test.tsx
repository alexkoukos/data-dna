import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { incident, metrics, mockApi, tool } from "../../test/fixtures";
import IncidentsPage from "./IncidentsPage";
import OverviewPage from "./OverviewPage";
import SecurityLayout from "./SecurityLayout";
import ToolsPage from "./ToolsPage";

afterEach(() => vi.unstubAllGlobals());

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/security" element={<SecurityLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="tools" element={<ToolsPage />} />
          <Route path="incidents" element={<IncidentsPage />} />
        </Route>
        <Route path="/chat" element={<p>chat</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Overview", () => {
  it("shows a skeleton, then the four numbers and recent incidents", async () => {
    mockApi({
      "/v1/metrics": metrics,
      "/v1/incidents": { total: 664, items: [incident(1), incident(2, { decision: "block" })] },
    });
    renderAt("/security");
    expect(screen.getByRole("status", { name: "Loading the overview" })).toBeInTheDocument();
    expect(await screen.findByText("9,769")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getByText("Down 6 from the week before")).toBeInTheDocument();
    expect(screen.getByText("Demo data")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review all 664 incidents" })).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
  });

  it("explains the empty state and points to the chat", async () => {
    mockApi({
      "/v1/metrics": { ...metrics, prompts_checked: 0, zero_llm_share: null },
      "/v1/incidents": { total: 0, items: [] },
    });
    renderAt("/security");
    expect(await screen.findByText("Nothing checked yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Company Chat" })).toBeInTheDocument();
  });

  it("shows a friendly error and recovers on retry", async () => {
    mockApi({ "/v1/metrics": "fail", "/v1/incidents": "fail" });
    renderAt("/security");
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not load the overview.");
    mockApi({ "/v1/metrics": metrics, "/v1/incidents": { total: 0, items: [] } });
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("9,769")).toBeInTheDocument();
  });
});

describe("AI tools", () => {
  const tools = [
    tool(1, { name: "Zed Approved", approval: "approved", risk: "low", alternative: null }),
    tool(2, { name: "Big Unapproved", requests: 900 }),
    tool(3, { name: "Small Unapproved", requests: 10 }),
    tool(4, { name: "Mid Tolerated", approval: "tolerated", risk: "medium" }),
  ];

  it("lists unapproved tools first, busiest first, with the approved alternative", async () => {
    mockApi({ "/v1/inventory": tools });
    renderAt("/security/tools");
    const items = await screen.findAllByRole("heading", { level: 3 });
    expect(items.map((h) => h.textContent)).toEqual([
      "Big Unapproved",
      "Small Unapproved",
      "Mid Tolerated",
      "Zed Approved",
    ]);
    expect(screen.getAllByText("Use Company AI instead.")).toHaveLength(3);
    expect(screen.getAllByRole("img", { name: /Requests per day/ })).toHaveLength(4);
  });

  it("filters by approval and says when a group is empty", async () => {
    mockApi({ "/v1/inventory": tools.slice(0, 2) });
    renderAt("/security/tools");
    await screen.findByText("Big Unapproved");
    await userEvent.click(screen.getByRole("button", { name: "Unapproved (1)" }));
    expect(screen.queryByText("Zed Approved")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Tolerated (0)" }));
    expect(screen.getByText("Nothing in this group")).toBeInTheDocument();
  });

  it("shows an error state", async () => {
    mockApi({ "/v1/inventory": "fail" });
    renderAt("/security/tools");
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not load the AI tools.");
  });
});

describe("Incidents", () => {
  it("lists incidents in plain words and never a raw value", async () => {
    mockApi({
      "/v1/incidents": { total: 1, items: [incident(1, { reasons: ["Contains iban"] })] },
    });
    renderAt("/security/incidents");
    const summary = await screen.findByText("Your message contains a bank account number (IBAN).");
    expect(summary).toBeInTheDocument();
    // Details open on click; only the masked preview is ever there.
    await userEvent.click(summary);
    expect(screen.getByText("AK••••••••••••••MPLE")).toBeInTheDocument();
    expect(screen.getByText("Showing 1 of 1, newest first.")).toBeInTheDocument();
  });

  it("filters by outcome through the API", async () => {
    const api = mockApi({ "/v1/incidents": { total: 0, items: [] } });
    renderAt("/security/incidents");
    expect(await screen.findByText("No incidents here")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Blocked" }));
    await screen.findByText("No incidents here");
    expect(String(api.mock.calls.at(-1)![0])).toContain("decision=block");
  });

  it("loads more with the right offset and appends", async () => {
    const api = mockApi({
      "/v1/incidents": (url: string) =>
        url.includes("offset=0")
          ? { total: 3, items: [incident(1), incident(2)] }
          : { total: 3, items: [incident(3)] },
    });
    renderAt("/security/incidents");
    await screen.findByText("Showing 2 of 3, newest first.");
    await userEvent.click(screen.getByRole("button", { name: "Show more" }));
    expect(await screen.findByText("Showing 3 of 3, newest first.")).toBeInTheDocument();
    expect(String(api.mock.calls.at(-1)![0])).toContain("offset=2");
    expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
    expect(within(screen.getByRole("list")).getAllByRole("listitem")).toHaveLength(3);
  });

  it("shows an error state with retry", async () => {
    mockApi({ "/v1/incidents": "fail" });
    renderAt("/security/incidents");
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not load the incidents.");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
