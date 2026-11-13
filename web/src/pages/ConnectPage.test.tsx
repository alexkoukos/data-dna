import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../test/fixtures";
import { buildSnippets, gatewayUrl } from "../lib/snippets";
import ConnectPage from "./ConnectPage";

const key = { key: "sk-test-key-123", default_model: "demo-mock" };

beforeEach(() => window.localStorage.clear());
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("snippets", () => {
  it("builds the address from the page host and puts address and key in the code", () => {
    const url = gatewayUrl({ protocol: "http:", hostname: "example.test" });
    expect(url).toBe("http://example.test:4000/v1");
    const py = buildSnippets(url, "sk-abc", "demo-mock")[0];
    expect(py.code).toContain('base_url="http://example.test:4000/v1"');
    expect(py.code).toContain('api_key="sk-abc"');
  });

  it("marks Claude Code and MCP as not available instead of faking a snippet", () => {
    const rest = buildSnippets("u", "k", "m").filter((s) => ["claude-code", "mcp"].includes(s.id));
    expect(rest).toHaveLength(2);
    expect(rest.every((s) => s.code === null && s.note.startsWith("Not available"))).toBe(true);
  });
});

describe("ConnectPage", () => {
  it("shows a skeleton, then the address, a hidden key and the waiting status", async () => {
    mockApi({ "/v1/keys": key, "/seen": { seen: false } });
    render(<ConnectPage />);
    expect(screen.getByRole("status", { name: "Loading your connection details" })).toBeVisible();
    expect(await screen.findByLabelText("Gateway address")).toHaveValue("http://localhost:4000/v1");
    expect(screen.getByLabelText("Personal key")).not.toHaveValue("sk-test-key-123");
    expect(screen.getByText(/Waiting for first request/)).toBeInTheDocument();
  });

  it("reveals the key and copies it", async () => {
    mockApi({ "/v1/keys": key, "/seen": { seen: false } });
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    render(<ConnectPage />);
    await screen.findByLabelText("Personal key");
    await user.click(screen.getByRole("button", { name: "Show personal key" }));
    expect(screen.getByLabelText("Personal key")).toHaveValue("sk-test-key-123");
    await user.click(screen.getByRole("button", { name: "Copy personal key" }));
    expect(writeText).toHaveBeenCalledWith("sk-test-key-123");
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });

  it("switches tabs and explains the ones that are not built", async () => {
    mockApi({ "/v1/keys": key, "/seen": { seen: false } });
    const user = userEvent.setup();
    render(<ConnectPage />);
    await screen.findByRole("tab", { name: "curl" });
    await user.click(screen.getByRole("tab", { name: "curl" }));
    expect(screen.getByText(/Authorization: Bearer sk-test-key-123/)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Claude Code" }));
    expect(screen.getByText(/Not available yet/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Copy this code" })).not.toBeInTheDocument();
  });

  it("turns to Connected once the gateway has seen a request", async () => {
    mockApi({ "/v1/keys": key, "/seen": { seen: true } });
    render(<ConnectPage />);
    expect(await screen.findByText(/Connected\. The gateway has checked/)).toBeInTheDocument();
  });

  it("keeps polling while waiting", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let seen = false;
    mockApi({ "/v1/keys": key, "/seen": () => ({ seen }) });
    render(<ConnectPage />);
    await screen.findByText(/Waiting for first request/);
    seen = true;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3100);
    });
    expect(await screen.findByText(/Connected\./)).toBeInTheDocument();
  });

  it("offers a retry when the key cannot be created", async () => {
    mockApi({ "/v1/keys": "fail" });
    render(<ConnectPage />);
    expect(await screen.findByText("We could not load your connection details.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Try again" })).toBeVisible();
  });
});
