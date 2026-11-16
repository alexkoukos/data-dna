import type { TraceStep } from "../lib/securityApi";

/** Presentational: which checks fired for one decision, in the order they ran (X23). */
export function WhyPanel({ trace, shadow }: { trace: TraceStep[]; shadow?: boolean }) {
  if (trace.length === 0) {
    return (
      <p className="mt-1 text-ink-700">
        This incident was recorded before the step-by-step explanation existed.
      </p>
    );
  }
  return (
    <>
      {shadow ? (
        <p className="mt-1 font-semibold text-warn-fg">
          Shadow mode was on: this is what the policy would have done. Nothing was changed.
        </p>
      ) : null}
      <ol className="mt-2 space-y-2">
        {trace.map((s, i) => (
          <li
            key={`${s.layer}-${i}`}
            className="rounded-xl border border-ink-200 bg-ink-50 p-3 text-sm"
          >
            <span className="font-semibold text-ink-900">{s.layer}</span>
            {s.score !== null ? (
              <span className="ml-2 text-ink-600">score {Math.round(s.score * 100)}%</span>
            ) : null}
            <p className="text-ink-700">{s.detail}</p>
          </li>
        ))}
      </ol>
    </>
  );
}
