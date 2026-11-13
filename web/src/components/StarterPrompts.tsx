import { Thyro } from "./Thyro";

const STARTERS = [
  { title: "Summarize notes", text: "Summarize these meeting notes in five bullet points." },
  {
    title: "Try a bank account number",
    text: "Can you check if this IBAN looks right? GR1601101250000000012300695",
  },
  {
    title: "Try an access key",
    text: "Why does my deploy fail with the key AKIAIOSFODNN7EXAMPLE?",
  },
];

/** Presentational: empty state. Shows what the chat does and lets people try it in one tap. */
export function StarterPrompts({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="rounded-lg border border-dashed border-ink-300 bg-white p-6">
      <div className="flex flex-wrap items-center gap-4">
        <Thyro pose="master" size={128} />
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold text-ink-900">Ask anything</h2>
          <p className="mt-1 max-w-prose text-ink-600">
            Every message is checked at the gate before it is sent, so private data stays inside the
            company. Pick one to see how it works.
          </p>
        </div>
      </div>
      <ul className="mt-4 grid gap-2 sm:grid-cols-3">
        {STARTERS.map((s) => (
          <li key={s.title}>
            <button
              type="button"
              onClick={() => onPick(s.text)}
              className="min-h-11 w-full rounded-md border border-ink-200 bg-ink-50 px-3 py-3 text-left text-sm font-medium text-ink-700 hover:bg-brand-50"
            >
              {s.title}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
