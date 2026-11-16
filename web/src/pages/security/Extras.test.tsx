import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { incident, mockApi } from "../../test/fixtures";
import HistoryPage from "./HistoryPage";
import ImpactPage from "./ImpactPage";

afterEach(() => vi.unstubAllGlobals());

describe("Impact (X18, X19, X20)", () => {
  const roi = {
    days: 30,
    leaks_stopped: 12,
    would_have_stopped: 3,
    by_category: { iban: 7, secret: 5 },
    exposure_eur: 26000,
    cost_avoided_eur: 2600,
    assumptions: {
      likelihood: 0.1,
      unit_cost_eur: { iban: 150 },
      document_cost_eur: { restricted: 10000 },
      note: "Illustrative estimates.",
    },
    tools: [
      {
        name: "ChatGPT (personal)",
        approval: "unapproved",
        risk: "high",
        requests: 100,
        risk_score: 300,
      },
    ],
  };
  it("shows the estimate with its assumptions, the weekly lines and coaching", async () => {
    mockApi({
      "/v1/roi": roi,
      "/v1/weekly-summary": {
        headline: "2 blocked, 9 incidents in the last 7 days",
        lines: ["9 incidents this week."],
        week: {},
        previous: {},
      },
      "/v1/coaching": { shown: 4, accepted: 3, acceptance_rate: 0.75 },
    });
    render(<ImpactPage />);
    expect(await screen.findByText("€2,600")).toBeInTheDocument();
    expect(screen.getByText(/An estimate: 10% of the €26,000 exposure/)).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("2 blocked, 9 incidents in the last 7 days")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /ChatGPT \(personal\)/ })).toBeInTheDocument();
    expect(screen.getByText(/Shadow mode would also have stopped 3 more/)).toBeInTheDocument();
  });
  it("offers a retry when the numbers cannot load", async () => {
    mockApi({ "/v1/roi": "fail", "/v1/weekly-summary": "fail", "/v1/coaching": "fail" });
    render(<ImpactPage />);
    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

describe("History (X24)", () => {
  it("replays one person's masked incidents", async () => {
    mockApi({
      "/v1/users/u-1/history": {
        subject: "u-1",
        found: true,
        total: 1,
        by_decision: { mask: 1 },
        items: [incident(1, { user: "u-1" })],
      },
      "/v1/documents": [],
    });
    render(
      <MemoryRouter initialEntries={["/security/history?user=u-1"]}>
        <HistoryPage />
      </MemoryRouter>,
    );
    expect(await screen.findByLabelText("History of u-1")).toHaveTextContent("1 incidents");
    expect(screen.getByText("AK••••••••••••••MPLE")).toBeInTheDocument();
  });
  it("starts with a prompt to choose someone", async () => {
    mockApi({ "/v1/documents": [] });
    render(
      <MemoryRouter>
        <HistoryPage />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Pick a person or a document")).toBeInTheDocument();
  });
});
