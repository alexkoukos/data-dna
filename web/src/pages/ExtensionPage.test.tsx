import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../test/fixtures";
import ExtensionPage from "./ExtensionPage";

afterEach(() => vi.unstubAllGlobals());

const users = [
  { user: "u-aaaa1111", team: "Sales" },
  { user: "u-bbbb2222", team: "Legal" },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ExtensionPage />
    </MemoryRouter>,
  );
}

describe("Get the extension", () => {
  it("offers the download, the install steps and the five samples", async () => {
    mockApi({
      "/api/v1/demo-users": users,
      "/samples/en/": "Some sample text",
    });
    renderPage();
    const download = screen.getByRole("link", { name: /Download sentry-extension.zip/ });
    expect(download).toHaveAttribute("href", "/extension.zip");
    expect(screen.getByText(/Load unpacked/)).toBeInTheDocument();
    const list = screen.getByRole("list", { name: "Sample texts" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(5);
    for (const outcome of ["Allowed", "Masked", "Warned", "Answered locally", "Blocked"]) {
      expect(within(list).getByText(outcome)).toBeInTheDocument();
    }
    expect((await within(list).findAllByText(/Some sample text/)).length).toBe(5);
  });

  it("shows a pairing code for the chosen person", async () => {
    mockApi({
      "/api/v1/demo-users": users,
      "/api/v1/pair/code": { code: "482913", user: "u-bbbb2222", team: "Legal", expires_in: 600 },
      "/samples/": "x",
    });
    renderPage();
    const select = await screen.findByLabelText("Pair as this person");
    const show = screen.getByRole("button", { name: "Show pairing code" });
    expect(show).toBeDisabled();
    await userEvent.selectOptions(select, "u-bbbb2222");
    await userEvent.click(show);
    expect(await screen.findByText("482913")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("u-bbbb2222 from Legal");
  });

  it("says pairing is off when there are no demo users", async () => {
    mockApi({ "/api/v1/demo-users": [], "/samples/": "x" });
    renderPage();
    expect(await screen.findByText(/Pairing codes are a demo feature/)).toBeInTheDocument();
  });

  it("explains when the sample files are not served", async () => {
    mockApi({ "/api/v1/demo-users": users, "/samples/": "fail" });
    renderPage();
    expect((await screen.findAllByText(/sample files are not served here/)).length).toBe(5);
  });

  it("switches the samples to Greek", async () => {
    const fn = mockApi({ "/api/v1/demo-users": users, "/samples/": "text" });
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Ελληνικά" }));
    expect(fn.mock.calls.some(([u]) => String(u).includes("/samples/el/1-allow.txt"))).toBe(true);
  });
});
