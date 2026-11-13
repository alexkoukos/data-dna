import { useEffect, useState } from "react";
import { EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import { IncidentHeader, IncidentRow } from "../../components/IncidentRow";
import { formatNumber } from "../../lib/format";
import { fetchIncidents, type Decision, type Incident } from "../../lib/securityApi";

type Filter = Exclude<Decision, "allow"> | "all";
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "block", label: "Blocked" },
  { id: "warn", label: "Warned" },
  { id: "mask", label: "Masked" },
  { id: "local", label: "Answered locally" },
];

type View =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; items: Incident[]; total: number };

/** Loads one filter's incidents. Remounted (via `key`) when the filter changes. */
function IncidentList({ filter }: { filter: Filter }) {
  const [view, setView] = useState<View>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchIncidents(filter, 0).then(
      (page) => !cancelled && setView({ status: "ready", items: page.items, total: page.total }),
      () => !cancelled && setView({ status: "error" }),
    );
    return () => {
      cancelled = true;
    };
  }, [filter, attempt]);

  const showMore = (shown: Incident[]) => {
    setLoadingMore(true);
    fetchIncidents(filter, shown.length).then(
      (page) => {
        setView({ status: "ready", items: [...shown, ...page.items], total: page.total });
        setLoadingMore(false);
      },
      () => {
        setView({ status: "error" });
        setLoadingMore(false);
      },
    );
  };

  if (view.status === "loading") {
    return (
      <div role="status" aria-label="Loading incidents" className="space-y-2">
        {[0, 1, 2].map((n) => (
          <Skeleton key={n} className="h-12" />
        ))}
      </div>
    );
  }
  if (view.status === "error") {
    return (
      <ErrorPanel
        what="the incidents"
        onRetry={() => {
          setView({ status: "loading" });
          setAttempt((n) => n + 1);
        }}
      />
    );
  }
  if (view.items.length === 0) {
    return (
      <EmptyPanel title="No incidents here">
        <p>
          Nothing matches this filter. When a message is masked, warned or blocked it shows up here.
        </p>
      </EmptyPanel>
    );
  }
  return (
    <>
      <p className="text-sm text-ink-600" aria-live="polite">
        Showing {formatNumber(view.items.length)} of {formatNumber(view.total)}, newest first.
      </p>
      <div className="mt-3">
        <IncidentHeader />
        <ul className="overflow-hidden rounded-lg border border-ink-200">
          {view.items.map((i) => (
            <IncidentRow key={i.id} incident={i} />
          ))}
        </ul>
      </div>
      {view.items.length < view.total ? (
        <button
          type="button"
          disabled={loadingMore}
          onClick={() => showMore(view.items)}
          className="mt-4 min-h-11 rounded-md border border-ink-300 bg-white px-4 text-sm font-semibold text-ink-900 hover:bg-ink-100 disabled:border-ink-200 disabled:bg-ink-100 disabled:text-ink-600"
        >
          {loadingMore ? "Loading…" : "Show more"}
        </button>
      ) : null}
    </>
  );
}

/** Container: incident list with a filter by outcome. */
export default function IncidentsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  return (
    <>
      <p className="max-w-prose text-ink-600">
        Messages that were masked, warned, blocked or kept inside. No message text is stored, only a
        masked preview.
      </p>
      <div role="group" aria-label="Filter by outcome" className="mt-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={`min-h-11 rounded-md border px-3 text-sm font-medium ${filter === f.id ? "border-brand-600 bg-brand-50 text-brand-700" : "border-ink-300 bg-white text-ink-700 hover:bg-ink-100"}`}
          >
            {f.label}
          </button>
        ))}
      </div>
      <div className="mt-4">
        <IncidentList key={filter} filter={filter} />
      </div>
    </>
  );
}
