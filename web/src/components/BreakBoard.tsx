import type { Board } from "../lib/breakItApi";
import { kindLabel } from "../lib/breakItApi";

/** Today's break-it numbers. Misses show the masked preview and the kind, never the raw text. */
export function BreakBoard({ board }: { board: Board }) {
  const rate = board.catch_rate === null ? "–" : `${board.catch_rate}%`;
  const stats = [
    { label: "Attempts today", value: String(board.attempts) },
    { label: "Stopped", value: String(board.stopped) },
    { label: "Got through", value: String(board.got_through) },
    { label: "Catch rate", value: rate },
  ];
  return (
    <section aria-label="Leaderboard" className="mt-10">
      <h2 className="text-lg font-semibold text-ink-900">Today's leaderboard</h2>
      <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="rounded-2xl border border-ink-200 bg-white p-4">
            <dt className="text-sm text-ink-600">{s.label}</dt>
            <dd className="mt-1 text-2xl font-semibold text-ink-900">{s.value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold text-ink-900">What got through</h3>
          {board.misses.length === 0 ? (
            <p className="mt-2 text-sm text-ink-600">
              Nothing has got through today. Try to be the first.
            </p>
          ) : (
            <ul className="mt-2 divide-y divide-ink-100 rounded-2xl border border-ink-200 bg-white">
              {board.misses.map((m) => (
                <li key={m.id} className="px-4 py-3 text-sm">
                  <p className="font-medium text-ink-900">{kindLabel(m.kind)}</p>
                  <p className="break-words text-ink-600">{m.preview}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-ink-900">Top breakers</h3>
          {board.top_breakers.length === 0 ? (
            <p className="mt-2 text-sm text-ink-600">
              Add a nickname and send a real miss to the review queue to appear here.
            </p>
          ) : (
            <ol className="mt-2 divide-y divide-ink-100 rounded-2xl border border-ink-200 bg-white">
              {board.top_breakers.map((b) => (
                <li key={b.nickname} className="flex justify-between gap-3 px-4 py-3 text-sm">
                  <span className="break-words font-medium text-ink-900">{b.nickname}</span>
                  <span className="shrink-0 text-ink-600">
                    {b.approved} approved, {b.submitted} sent
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </section>
  );
}
