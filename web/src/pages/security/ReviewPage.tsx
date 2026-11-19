import { useState } from "react";
import { EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import { kindLabel, fetchQueue, review, type Candidate } from "../../lib/breakItApi";
import { useFetch } from "../../lib/useFetch";

const EXPECTED: Record<string, string> = { mask: "mask it", warn: "warn", block: "block it" };

function Row({
  c,
  reviewer,
  onDone,
}: {
  c: Candidate;
  reviewer: string;
  onDone: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act(verb: "approve" | "reject") {
    setBusy(true);
    setError(null);
    try {
      await review(c.id, verb, reviewer);
      onDone(
        verb === "approve"
          ? "Approved. It is now a row in the test set (source: breakit)."
          : "Rejected. The text was deleted.",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "That could not be saved.");
      setBusy(false);
    }
  }

  return (
    <li className="rounded-2xl border border-ink-200 bg-surface p-4">
      <p className="text-sm text-ink-600">
        {kindLabel(c.kind)} · should {EXPECTED[c.expected_decision] ?? c.expected_decision} · the
        gate said {c.got_decision}
        {c.nickname ? ` · from ${c.nickname}` : ""}
      </p>
      <pre
        tabIndex={0}
        aria-label="Submitted text"
        className="mt-2 overflow-x-auto whitespace-pre-wrap break-words rounded-lg bg-ink-900 p-3 text-sm text-ink-50"
      >
        {c.text}
      </pre>
      {error ? (
        <p role="alert" className="mt-2 text-sm font-medium text-block-fg">
          {error}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy || !reviewer.trim()}
          onClick={() => void act("approve")}
          className="min-h-11 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-[#04141a] hover:bg-brand-700 disabled:opacity-60"
        >
          Approve
        </button>
        <button
          type="button"
          disabled={busy || !reviewer.trim()}
          onClick={() => void act("reject")}
          className="min-h-11 rounded-lg border border-ink-300 bg-surface px-5 text-sm font-semibold text-ink-900 hover:bg-ink-100 disabled:opacity-60"
        >
          Reject and delete
        </button>
      </div>
    </li>
  );
}

/** Security area: review what people say got through on /break-it before it joins the test set. */
export default function ReviewPage() {
  const [state, reload] = useFetch(fetchQueue);
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState<string | null>(null);

  return (
    <section aria-label="Break it review queue">
      <h2 className="text-lg font-semibold text-ink-900">Break it: review queue</h2>
      <p className="mt-1 max-w-prose text-ink-600">
        Each row is a text someone chose to submit as a test case. This is the only place the raw
        text is kept. Approving adds it to <code>data/eval/attacks_scripts.csv</code> and removes
        the text here; rejecting deletes it at once.
      </p>
      <label htmlFor="reviewer" className="mt-4 block text-sm font-semibold text-ink-900">
        Your name (written to the audit log)
      </label>
      <input
        id="reviewer"
        value={reviewer}
        onChange={(e) => setReviewer(e.target.value)}
        autoComplete="off"
        className="mt-1 min-h-11 w-full rounded-lg border border-ink-300 bg-surface px-3 text-ink-900 sm:w-72"
      />
      {note ? (
        <p role="status" className="mt-4 rounded-2xl bg-allow-bg p-3 text-allow-fg">
          {note}
        </p>
      ) : null}
      <div className="mt-4">
        {state.status === "loading" ? <Skeleton className="h-24 w-full" /> : null}
        {state.status === "error" ? <ErrorPanel what="the review queue" onRetry={reload} /> : null}
        {state.status === "ready" && state.data.length === 0 ? (
          <EmptyPanel title="Nothing to review">
            New submissions from /break-it show up here.
          </EmptyPanel>
        ) : null}
        {state.status === "ready" && state.data.length > 0 ? (
          <ul className="space-y-4">
            {state.data.map((c) => (
              <Row
                key={c.id}
                c={c}
                reviewer={reviewer}
                onDone={(m) => {
                  setNote(m);
                  reload();
                }}
              />
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}
