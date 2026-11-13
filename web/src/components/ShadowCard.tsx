import type { ShadowStatus } from "../lib/securityApi";

const ORDER = ["block", "local", "warn", "mask"] as const;

/** Presentational: the shadow-mode switch and what the policy would have done (X11). */
export function ShadowCard({
  status,
  busy,
  error,
  onToggle,
}: {
  status: ShadowStatus;
  busy: boolean;
  error: string | null;
  onToggle: (next: boolean) => void;
}) {
  const parts = ORDER.filter((d) => (status.would_have[d] ?? 0) > 0).map((d) =>
    `${status.would_have[d]} ${d === "local" ? "answered locally" : `${d}ed`}`.replace(
      "blocked",
      "blocked",
    ),
  );
  return (
    <section
      aria-labelledby="shadow-h"
      className="mt-4 rounded-2xl border border-ink-200 bg-white p-4"
    >
      <h2 id="shadow-h" className="text-lg font-semibold text-ink-900">
        Shadow mode
      </h2>
      <p className="max-w-prose text-sm text-ink-700">
        Try your policies without stopping anyone. Every message goes through and the dashboard
        records what would have happened.
      </p>
      <button
        type="button"
        role="switch"
        aria-checked={status.enabled}
        disabled={busy}
        onClick={() => onToggle(!status.enabled)}
        className="mt-3 min-h-11 rounded-lg border border-ink-300 px-4 text-sm font-semibold text-ink-900 hover:bg-ink-100 disabled:opacity-60"
      >
        {status.enabled ? "Shadow mode is on. Turn it off" : "Shadow mode is off. Turn it on"}
      </button>
      <p className="mt-2 text-sm text-ink-700">
        {status.total === 0
          ? "Nothing recorded in shadow mode yet."
          : `Would have stopped or changed ${status.total} messages: ${parts.join(", ")}.`}
      </p>
      {error ? (
        <p role="alert" className="mt-2 text-sm font-semibold text-block-fg">
          {error}
        </p>
      ) : null}
    </section>
  );
}
