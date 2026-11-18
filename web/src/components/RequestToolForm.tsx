import { useState } from "react";
import { requestTool } from "../lib/toolRequestsApi";

/** An employee asks security to approve an AI tool: which tool and why. */
export function RequestToolForm({
  userId,
  team,
  initialTool = "",
  onClose,
}: {
  userId: string;
  team: string;
  initialTool?: string;
  onClose: () => void;
}) {
  const [tool, setTool] = useState(initialTool);
  const [reason, setReason] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  async function send() {
    setState("busy");
    setError(null);
    try {
      await requestTool({ user_id: userId, team, tool, reason });
      setState("sent");
    } catch (e) {
      setState("idle");
      setError(e instanceof Error ? e.message : "We could not send your request.");
    }
  }

  if (state === "sent") {
    return (
      <div
        role="status"
        className="rounded-lg border border-allow-fg/30 bg-allow-bg p-4 text-allow-fg"
      >
        <p className="font-semibold">Request sent.</p>
        <p className="mt-1 text-sm">
          Security will decide. You will see the answer here on your next message.
        </p>
        <button
          type="button"
          onClick={onClose}
          className="mt-3 min-h-11 rounded-md border border-ink-300 bg-white px-4 text-sm font-medium text-ink-900"
        >
          Close
        </button>
      </div>
    );
  }
  return (
    <form
      aria-label="Request an AI tool"
      className="rounded-lg border border-ink-200 bg-white p-4"
      onSubmit={(e) => {
        e.preventDefault();
        void send();
      }}
    >
      <h2 className="text-base font-semibold text-ink-900">Request approval for an AI tool</h2>
      <label htmlFor="req-tool" className="mt-3 block text-sm font-semibold text-ink-900">
        Tool
      </label>
      <input
        id="req-tool"
        value={tool}
        maxLength={80}
        onChange={(e) => setTool(e.target.value)}
        className="mt-1 min-h-11 w-full rounded-lg border border-ink-300 bg-white px-3 text-ink-900"
      />
      <label htmlFor="req-reason" className="mt-3 block text-sm font-semibold text-ink-900">
        Why do you need it?
      </label>
      <textarea
        id="req-reason"
        value={reason}
        maxLength={500}
        rows={3}
        onChange={(e) => setReason(e.target.value)}
        className="mt-1 w-full rounded-lg border border-ink-300 bg-white p-3 text-ink-900"
      />
      <p className="mt-2 text-sm text-ink-600">
        For team: <span className="font-medium text-ink-900">{team}</span>. Do not put sensitive
        data in the reason.
      </p>
      {error ? (
        <p role="alert" className="mt-2 text-sm font-medium text-block-fg">
          {error}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={state === "busy" || !tool.trim() || !reason.trim()}
          aria-busy={state === "busy"}
          className="min-h-11 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {state === "busy" ? "Sending…" : "Send request"}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="min-h-11 rounded-lg px-3 text-sm font-medium text-ink-600 hover:bg-ink-100"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
