import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../../test/fixtures";
import { trendText, type Digest } from "../../lib/digestApi";
import DigestPage from "./DigestPage";

afterEach(() => vi.unstubAllGlobals());

const digest = (team: string, over: Partial<Digest> = {}): Digest => ({
  team,
  note: "Team-level counts only. This digest has no employee names and no message text.",
  start: "2026-11-06",
  end: "2026-11-13",
  incidents: 12,
  previous: 10,
  change: 2,
  change_pct: 20,
  outcomes: { mask: 8, block: 4 },
  categories: [{ category: "person_email_phone", count: 6 }],
  tools: [{ name: "ChatGPT (personal)", approval: "unapproved", count: 5 }],
  tips: ["Replace names with roles.", "Use Company AI instead of ChatGPT (personal)."],
  markdown: "# Weekly AI digest",
  email: { subject: `Weekly AI digest for ${team}`, body: "Hello,\n\nBody." },
  ...over,
});

const routes = (team = "Finance") => ({
  "/v1/digest/teams": ["Finance", "Sales"],
  "/v1/digest?team=Sales": digest("Sales", { incidents: 3, previous: 3, change: 0 }),
  "/v1/digest?team": digest(team),
});

describe("Weekly digest", () => {
  it("says up front that it has team-level counts only, and shows the first team", async () => {
    mockApi(routes());
    render(<DigestPage />);
    const article = await screen.findByRole("article", { name: "Digest for Finance" });
    expect(within(article).getByText(/no employee names and no message text/)).toBeInTheDocument();
    expect(
      within(article).getByText("12 this week, up by 2 (20%) on last week (10)."),
    ).toBeInTheDocument();
    expect(within(article).getByText("Masked")).toBeInTheDocument();
    expect(within(article).getByText("person email phone")).toBeInTheDocument();
    expect(within(article).getByText("Replace names with roles.")).toBeInTheDocument();
    const tools = within(article).getByRole("region", { name: "Tools" });
    expect(within(tools).getByText(/ChatGPT \(personal\)/)).toBeInTheDocument();
  });

  it("switches team", async () => {
    mockApi(routes());
    const user = userEvent.setup();
    render(<DigestPage />);
    await screen.findByRole("article", { name: "Digest for Finance" });
    await user.selectOptions(screen.getByLabelText("Team"), "Sales");
    expect(await screen.findByRole("article", { name: "Digest for Sales" })).toBeInTheDocument();
    expect(screen.getByText("3 this week, unchanged on last week (3).")).toBeInTheDocument();
  });

  it("copies the email draft and says nothing was sent", async () => {
    mockApi(routes());
    const user = userEvent.setup(); // installs its own clipboard, so ours goes in after
    const write = vi.fn(async () => undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: write },
      configurable: true,
    });
    render(<DigestPage />);
    await user.click(await screen.findByRole("button", { name: "Copy as email" }));
    expect(write).toHaveBeenCalledWith("Subject: Weekly AI digest for Finance\n\nHello,\n\nBody.");
    expect(await screen.findByText(/Nothing was sent/)).toBeInTheDocument();
  });

  it("shows the text to copy by hand when the clipboard is blocked", async () => {
    mockApi(routes());
    const user = userEvent.setup();
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn(async () => Promise.reject(new Error("no"))) },
      configurable: true,
    });
    render(<DigestPage />);
    await user.click(await screen.findByRole("button", { name: "Copy as email" }));
    expect(await screen.findByLabelText(/blocked copying/)).toHaveValue(
      "Subject: Weekly AI digest for Finance\n\nHello,\n\nBody.",
    );
  });

  it("links the Markdown export for the chosen team", async () => {
    mockApi(routes());
    render(<DigestPage />);
    const link = await screen.findByRole("link", { name: "Download Markdown" });
    expect(link).toHaveAttribute("href", "/api/v1/digest.md?team=Finance");
  });

  it("has an empty state when no team has incidents", async () => {
    mockApi({ "/v1/digest/teams": [] });
    render(<DigestPage />);
    expect(await screen.findByText("No digest yet")).toBeInTheDocument();
  });

  it("has an error state with a retry", async () => {
    mockApi({ "/v1/digest/teams": "fail" });
    render(<DigestPage />);
    expect(await screen.findByRole("button", { name: /try again|retry/i })).toBeInTheDocument();
  });
});

describe("trendText", () => {
  it("matches the brain's wording", () => {
    expect(trendText({ incidents: 8, previous: 10, change: -2, change_pct: -20 })).toBe(
      "8 this week, down by 2 (20%) on last week (10).",
    );
    expect(trendText({ incidents: 5, previous: 0, change: 5, change_pct: null })).toBe(
      "5 this week, none the week before.",
    );
  });
});
