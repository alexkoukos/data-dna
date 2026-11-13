import { useEffect, useState } from "react";
import { OutcomeChip } from "../components/OutcomeChip";
import { CheckIcon } from "../components/icons";
import {
  fetchExamples,
  kindLabel,
  tryText,
  type TryExample,
  type TryResult,
} from "../lib/breakItApi";

function Verdict({ result }: { result: TryResult }) {
  const caught = result.decision !== "allow";
  return (
    <section aria-label="Result" className="mt-8">
      <div className="flex flex-wrap items-center gap-3">
        <OutcomeChip outcome={result.decision} />
        <h2 className="text-lg font-semibold text-ink-900">
          {caught
            ? `Stopped by: ${result.caught_by ?? "the trick-cleaning step"}`
            : "Nothing caught this text"}
        </h2>
      </div>
      {caught ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-ink-900">
          {result.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 max-w-prose text-ink-600">
          It went through every level. If it should have been stopped, you found a gap: tell the
          team what you typed.
        </p>
      )}
      {result.decision === "mask" ? (
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-ink-900">What the AI would receive</h3>
          <pre
            tabIndex={0}
            aria-label="Masked text"
            className="mt-1 overflow-x-auto whitespace-pre-wrap rounded-lg bg-ink-900 p-4 text-sm text-ink-50"
          >
            {result.masked_text}
          </pre>
        </div>
      ) : null}
      <h3 className="mt-6 text-sm font-semibold text-ink-900">What each level saw</h3>
      <ol className="mt-2 divide-y divide-ink-100 overflow-hidden rounded-2xl border border-ink-200 bg-white">
        {result.layers.map((l) => (
          <li key={l.id} className="flex items-start gap-3 px-4 py-3">
            <span className="w-6 shrink-0 pt-0.5 text-sm text-ink-600">{l.level}</span>
            <div className="min-w-0 flex-1">
              <p className="font-medium text-ink-900">{l.label}</p>
              {l.fired ? <p className="break-words text-sm text-ink-600">{l.detail}</p> : null}
            </div>
            {l.fired ? (
              <span className="inline-flex shrink-0 items-center gap-1.5 text-sm font-semibold text-allow-fg">
                <CheckIcon />
                Found something
              </span>
            ) : (
              <span className="shrink-0 text-sm text-ink-600">Nothing found</span>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

/** Container: type anything, see the decision, the reasons and which level caught it (X1). */
export default function BreakItPage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<TryResult | null>(null);
  const [examples, setExamples] = useState<TryExample[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchExamples().then(
      (e) => !cancelled && setExamples(e),
      () => undefined,
    );
    return () => {
      cancelled = true;
    };
  }, []);

  async function check() {
    setBusy(true);
    setError(null);
    try {
      setResult(await tryText(text));
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "We could not check that text.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-2xl font-semibold text-ink-900">Try to break it</h1>
      <p className="mt-2 max-w-prose text-ink-600">
        Type anything you think the gateway will miss: a bank account with spaces, a name in Latin
        letters, a key hidden in code. You see what it decided and which level caught it. Nothing
        you type here is saved, and the identifiers in the examples are invented.
      </p>
      <form
        className="mt-6"
        onSubmit={(e) => {
          e.preventDefault();
          void check();
        }}
      >
        <label htmlFor="attack" className="block text-sm font-semibold text-ink-900">
          Text to check
        </label>
        <textarea
          id="attack"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          className="mt-1 w-full rounded-lg border border-ink-300 bg-white p-3 text-ink-900"
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy || text.trim().length === 0}
            aria-busy={busy}
            className="min-h-11 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {busy ? "Checking…" : "Check it"}
          </button>
          {text ? (
            <button
              type="button"
              onClick={() => {
                setText("");
                setResult(null);
                setError(null);
              }}
              className="min-h-11 rounded-lg px-3 text-sm font-medium text-ink-600 hover:bg-ink-100"
            >
              Clear
            </button>
          ) : null}
        </div>
      </form>
      {examples.length > 0 ? (
        <section aria-label="Examples" className="mt-6">
          <h2 className="text-sm font-semibold text-ink-900">Not sure where to start? Try one</h2>
          <ul className="mt-2 flex flex-wrap gap-2">
            {examples.map((x) => (
              <li key={x.category}>
                <button
                  type="button"
                  onClick={() => {
                    setText(x.text);
                    setResult(null);
                    setError(null);
                  }}
                  className="min-h-11 rounded-full border border-ink-300 bg-white px-4 text-sm font-medium text-ink-900 hover:bg-ink-100"
                >
                  {kindLabel(x.category)}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {error ? (
        <div
          role="alert"
          className="mt-6 rounded-2xl border border-block-fg/30 bg-block-bg p-4 text-block-fg"
        >
          <p className="font-semibold">{error}</p>
          <p className="mt-1 text-sm">
            Your text is still in the box. Press Check it to try again.
          </p>
        </div>
      ) : null}
      {result ? <Verdict result={result} /> : null}
    </main>
  );
}
