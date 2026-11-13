import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { incident, mockApi } from "../../test/fixtures";
import IncidentDetailPage from "./IncidentDetailPage";

afterEach(() => vi.unstubAllGlobals());

const reveal = (over = {}) => ({
  id: 5,
  incident_id: 7,
  requested_by: "Anna",
  reason: "Pasted a client contract",
  approved_by: null,
  status: "pending",
  ts: null,
  ...over,
});

const detail = (over = {}) => ({
  incident: incident(7, { decision: "mask", user: "u-ab12cd34" }),
  copy_code: null,
  document: null,
  timeline: [incident(3)],
  reveals: [],
  ...over,
});

function open() {
  return render(
    <MemoryRouter initialEntries={["/security/incidents/7"]}>
      <Routes>
        <Route path="/security/incidents/:id" element={<IncidentDetailPage />} />
        <Route path="/security/incidents" element={<p>list</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Incident detail", () => {
  it("shows what happened, a sealed pseudonym and the person's other incidents", async () => {
    mockApi({ "/v1/incidents/7": detail() });
    open();
    expect(screen.getByRole("status", { name: "Loading the incident" })).toBeInTheDocument();
    expect(await screen.findByText("What happened")).toBeInTheDocument();
    expect(screen.getByText("u-ab12cd34")).toBeInTheDocument();
    expect(screen.getByText(/real name stays sealed/)).toBeInTheDocument();
    expect(screen.getByText("No protected document was involved.")).toBeInTheDocument();
    expect(screen.getByText(/No marked copy was involved/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Other incidents from/ })).toBeInTheDocument();
  });

  it("shows the matched document and marked copy when there is one", async () => {
    mockApi({
      "/v1/incidents/7": detail({
        document: { id: 1, title: "Merger memo", sensitivity: "restricted" },
        copy_code: "K7QX",
      }),
    });
    open();
    expect(await screen.findByText("Merger memo")).toBeInTheDocument();
    expect(screen.getByText(/Marked copy K7QX/)).toBeInTheDocument();
  });

  it("needs a reason of ten characters before a reveal can be requested", async () => {
    mockApi({ "/v1/incidents/7": detail() });
    const user = userEvent.setup();
    open();
    const ask = await screen.findByRole("button", { name: "Request reveal" });
    expect(ask).toBeDisabled();
    await user.type(screen.getByLabelText("Your name"), "Anna");
    await user.type(screen.getByLabelText(/Why do you need/), "short");
    expect(ask).toBeDisabled();
    await user.type(screen.getByLabelText(/Why do you need/), " but long enough");
    expect(ask).toBeEnabled();
  });

  it("a pending request waits for a second person", async () => {
    mockApi({ "/v1/incidents/7": detail({ reveals: [reveal()] }) });
    open();
    expect(await screen.findByText(/Waiting for a second person/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve the reveal" })).toBeDisabled();
  });

  it("shows the server's plain refusal when the requester approves their own request", async () => {
    mockApi({ "/v1/incidents/7": detail({ reveals: [reveal()] }) });
    const user = userEvent.setup();
    open();
    await user.type(await screen.findByLabelText("Your name"), "Anna");
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "A second person must approve." }), {
            status: 422,
          }),
      ),
    );
    await user.click(screen.getByRole("button", { name: "Approve the reveal" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A second person must approve.");
  });

  it("shows the real name only after approval, and says the view was logged", async () => {
    mockApi({
      "/v1/incidents/7/identity": { pseudonym: "u-ab12cd34", display_name: "Maria Papadopoulou" },
      "/v1/incidents/7": detail({
        reveals: [reveal({ status: "approved", approved_by: "Nikos" })],
      }),
    });
    const user = userEvent.setup();
    open();
    expect(screen.queryByText(/Maria/)).not.toBeInTheDocument();
    await user.type(await screen.findByLabelText("Your name"), "Anna");
    await user.click(screen.getByRole("button", { name: "Show the real name" }));
    expect(await screen.findByText(/Real name: Maria Papadopoulou/)).toBeInTheDocument();
    expect(screen.getByText(/This view was logged/)).toBeInTheDocument();
  });

  it("offers a retry when the incident cannot be loaded", async () => {
    mockApi({ "/v1/incidents/7": "fail" });
    open();
    expect(await screen.findByText("We could not load this incident.")).toBeInTheDocument();
  });
});
