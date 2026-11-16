import { Link } from "react-router-dom";

/** Presentational: after Pyli acts on a message, point to the place where security sees it. */
export function NextStep() {
  return (
    <aside
      aria-label="Next step"
      className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-brand-600/30 bg-brand-50 p-4"
    >
      <p className="min-w-0 flex-1 text-sm text-ink-800">
        <span className="font-semibold">Pyli stepped in.</span> Security can now see this message as
        an incident.
      </p>
      <Link
        to="/security/incidents"
        className="inline-flex min-h-11 items-center rounded-md bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700"
      >
        See it in the security view
      </Link>
    </aside>
  );
}
