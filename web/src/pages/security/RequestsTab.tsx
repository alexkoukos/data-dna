import { useState } from "react";
import { EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import {
  CATEGORIES,
  decideRequest,
  fetchRequests,
  type ToolRequest,
} from "../../lib/toolRequestsApi";
import { useFetch } from "../../lib/useFetch";

function PendingCard({
  r,
  reviewer,
  onDone,
}: {
  r: ToolRequest;
  reviewer: string;
  onDone: (m: string) => void;
}) {
  const [risk, setRisk] = useState("medium");
  const [allowed, setAllowed] = useState<string[]>([]);
  const [alternative, setAlternative] = useState("Company AI");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(approve: boolean) {
    setBusy(true);
    setError(null);
    try {
      await decideRequest(r.id, {
        reviewer,
        approve,
        risk: approve ? risk : undefined,
        allowed_categories: approve ? allowed : [],
        alternative: alternative.trim() || undefined,
        note,
      });
      onDone(approve ? `${r.tool} is now approved.` : `${r.tool} was rejected.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "That could not be saved.");
      setBusy(false);
    }
  }
  const toggle = (c: string) =>
    setAllowed((a) => (a.includes(c) ? a.filter((x) => x !== c) : [...a, c]));

  return (
    <li className="rounded-lg border border-ink-200 bg-surface p-4">
      <h3 className="text-base font-semibold text-ink-900">{r.tool}</h3>
      <p className="text-sm text-ink-600">
        Asked by {r.requester} ({r.team})
      </p>
      <p className="mt-2 max-w-prose text-ink-900">{r.reason}</p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor={`risk-${r.id}`} className="block text-sm font-semibold text-ink-900">
            Risk rating
          </label>
          <select
            id={`risk-${r.id}`}
            value={risk}
            onChange={(e) => setRisk(e.target.value)}
            className="mt-1 min-h-11 w-full rounded-lg border border-ink-300 bg-surface px-3"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <div>
          <label htmlFor={`alt-${r.id}`} className="block text-sm font-semibold text-ink-900">
            Approved alternative (optional)
          </label>
          <input
            id={`alt-${r.id}`}
            value={alternative}
            onChange={(e) => setAlternative(e.target.value)}
            className="mt-1 min-h-11 w-full rounded-lg border border-ink-300 bg-surface px-3"
          />
        </div>
      </div>
      <fieldset className="mt-4">
        <legend className="text-sm font-semibold text-ink-900">Data this tool may receive</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <label
              key={c}
              className="flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-ink-300 px-3 text-sm"
            >
              <input type="checkbox" checked={allowed.includes(c)} onChange={() => toggle(c)} />
              {c.replace(/_/g, " ")}
            </label>
          ))}
        </div>
      </fieldset>
      <label htmlFor={`note-${r.id}`} className="mt-4 block text-sm font-semibold text-ink-900">
        Note to the requester (optional)
      </label>
      <input
        id={`note-${r.id}`}
        value={note}
        maxLength={300}
        onChange={(e) => setNote(e.target.value)}
        className="mt-1 min-h-11 w-full rounded-lg border border-ink-300 bg-surface px-3"
      />
      {error ? (
        <p role="alert" className="mt-2 text-sm font-medium text-block-fg">
          {error}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy || !reviewer.trim()}
          onClick={() => void decide(true)}
          className="min-h-11 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-[#04141a] hover:bg-brand-700 disabled:opacity-60"
        >
          Approve
        </button>
        <button
          type="button"
          disabled={busy || !reviewer.trim()}
          onClick={() => void decide(false)}
          className="min-h-11 rounded-lg border border-ink-300 bg-surface px-5 text-sm font-semibold text-ink-900 hover:bg-ink-100 disabled:opacity-60"
        >
          Reject
        </button>
      </div>
    </li>
  );
}

/** Security: requests for AI tools. Approving updates the inventory and risk per tool. */
export default function RequestsTab({ onChanged }: { onChanged: () => void }) {
  const [state, reload] = useFetch(fetchRequests);
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState<string | null>(null);

  if (state.status === "loading") return <Skeleton className="h-32 w-full" />;
  if (state.status === "error") return <ErrorPanel what="the requests" onRetry={reload} />;
  const pending = state.data.filter((r) => r.status === "pending");
  const decided = state.data.filter((r) => r.status !== "pending");

  return (
    <section aria-label="Tool requests">
      <p className="max-w-prose text-ink-600">
        Employees ask for AI tools from the chat. Approving a tool changes its approval and risk in
        the inventory. Every step is written to the audit log.
      </p>
      <label htmlFor="req-reviewer" className="mt-4 block text-sm font-semibold text-ink-900">
        Your name (written to the audit log)
      </label>
      <input
        id="req-reviewer"
        value={reviewer}
        onChange={(e) => setReviewer(e.target.value)}
        autoComplete="off"
        className="mt-1 min-h-11 w-full rounded-lg border border-ink-300 bg-surface px-3 sm:w-72"
      />
      {note ? (
        <p role="status" className="mt-4 rounded-lg bg-allow-bg p-3 text-allow-fg">
          {note}
        </p>
      ) : null}
      <h2 className="mt-6 text-lg font-semibold text-ink-900">Waiting ({pending.length})</h2>
      {pending.length === 0 ? (
        <div className="mt-2">
          <EmptyPanel title="No requests waiting">
            <p>New requests from the chat show up here.</p>
          </EmptyPanel>
        </div>
      ) : (
        <ul className="mt-2 space-y-3">
          {pending.map((r) => (
            <PendingCard
              key={r.id}
              r={r}
              reviewer={reviewer}
              onDone={(m) => {
                setNote(m);
                reload();
                onChanged();
              }}
            />
          ))}
        </ul>
      )}
      {decided.length > 0 ? (
        <>
          <h2 className="mt-8 text-lg font-semibold text-ink-900">Decided</h2>
          <ul className="mt-2 divide-y divide-ink-100 rounded-lg border border-ink-200 bg-surface">
            {decided.map((r) => (
              <li key={r.id} className="px-4 py-3 text-sm">
                <span className="font-medium text-ink-900">{r.tool}</span>{" "}
                <span className="text-ink-600">
                  {r.status === "approved" ? "approved" : "rejected"} by {r.decided_by}, asked by{" "}
                  {r.requester}
                </span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
