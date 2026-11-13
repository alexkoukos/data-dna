import { useState } from "react";
import { EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import { askPreset, fetchPresets, type Answer } from "../../lib/securityApi";
import { useFetch } from "../../lib/useFetch";

const HEADINGS: Record<string, string> = {
  team: "Team",
  tool: "Tool",
  incidents: "Incidents",
  approval: "Approval",
  requests: "Requests",
  decision: "Outcome",
  messages: "Messages",
  risk: "Risk",
  first_seen: "First seen",
  title: "Document",
  sensitivity: "Sensitivity",
  unapproved_tool_requests: "Requests to unapproved tools",
  client_data_incidents: "Client data caught",
};
const heading = (c: string) => HEADINGS[c] ?? c.replace(/_/g, " ");

function AnswerView({ answer }: { answer: Answer }) {
  return (
    <section aria-label="Answer" className="mt-6">
      <h2 className="text-lg font-semibold text-ink-900">{answer.question}</h2>
      {answer.rows.length === 0 ? (
        <div className="mt-3">
          <EmptyPanel title="Nothing found">
            <p>No rows match this question for the last few days. Try another question.</p>
          </EmptyPanel>
        </div>
      ) : (
        <div className="mt-3 overflow-x-auto rounded-lg border border-ink-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-200 text-ink-600">
              <tr>
                {answer.columns.map((c) => (
                  <th key={c} scope="col" className="px-4 py-3 font-semibold">
                    {heading(c)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {answer.rows.map((row, i) => (
                <tr key={i} className="border-b border-ink-100 last:border-0">
                  {row.map((cell, j) => (
                    <td key={j} className="px-4 py-3 text-ink-900">
                      {cell ?? "None"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <details className="mt-4 rounded-lg border border-ink-200 bg-white p-4">
        <summary className="min-h-11 cursor-pointer py-2 text-sm font-semibold text-ink-900">
          Show the SQL behind this answer
        </summary>
        <pre
          tabIndex={0}
          aria-label="SQL for this answer"
          className="mt-2 overflow-x-auto rounded-lg bg-ink-900 p-4 text-sm text-ink-50"
        >
          <code>{answer.sql}</code>
        </pre>
        <p className="mt-2 text-sm text-ink-600">
          {Object.entries(answer.parameters)
            .map(([k, v]) => `:${k} = ${v}`)
            .join(", ")}
          . Read-only: this question can only look, never change anything.
        </p>
      </details>
    </section>
  );
}

/** Container: preset analyst questions. The SQL is always shown next to the answer. */
export default function AskPage() {
  const [presets, reload] = useFetch(fetchPresets);
  const [active, setActive] = useState<string | null>(null);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(id: string) {
    setActive(id);
    setBusy(true);
    setError(null);
    try {
      setAnswer(await askPreset(id));
    } catch (e) {
      setAnswer(null);
      setError(e instanceof Error ? e.message : "We could not get the answer.");
    } finally {
      setBusy(false);
    }
  }

  if (presets.status === "loading") {
    return (
      <div role="status" aria-label="Loading questions" className="space-y-3">
        {[0, 1, 2].map((n) => (
          <Skeleton key={n} className="h-14" />
        ))}
      </div>
    );
  }
  if (presets.status === "error") return <ErrorPanel what="the questions" onRetry={reload} />;

  return (
    <>
      <p className="max-w-prose text-ink-600">
        Pick a question. You get a table and the exact SQL that produced it.
      </p>
      <ul className="mt-4 grid gap-2 sm:grid-cols-2">
        {presets.data.map((p) => (
          <li key={p.id}>
            <button
              type="button"
              aria-pressed={active === p.id}
              disabled={busy}
              onClick={() => ask(p.id)}
              className={`min-h-11 w-full rounded-lg border px-4 py-3 text-left text-sm font-medium ${active === p.id ? "border-brand-600 bg-brand-50 text-brand-700" : "border-ink-300 bg-white text-ink-900 hover:bg-ink-100"}`}
            >
              {p.question}
            </button>
          </li>
        ))}
      </ul>
      {busy ? (
        <div role="status" aria-label="Getting the answer" className="mt-6">
          <Skeleton className="h-40" />
        </div>
      ) : null}
      {error ? (
        <div role="alert" className="mt-6 rounded-lg bg-block-bg p-4 font-semibold text-block-fg">
          {error}
        </div>
      ) : null}
      {!busy && answer ? <AnswerView answer={answer} /> : null}
    </>
  );
}
