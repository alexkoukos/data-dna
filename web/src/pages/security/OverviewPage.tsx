import { Link } from "react-router-dom";
import { DemoBadge, EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import { IncidentRow } from "../../components/IncidentRow";
import { KpiCard } from "../../components/KpiCard";
import { formatNumber, formatPercent } from "../../lib/format";
import {
  fetchIncidents,
  fetchMetrics,
  type IncidentPage,
  type Metrics,
} from "../../lib/securityApi";
import { useFetch } from "../../lib/useFetch";

const load = () => Promise.all([fetchMetrics(), fetchIncidents("all", 0, 5)]);

function change(now: number, before: number): string {
  if (before === 0) return now === 0 ? "No change from the week before" : "New this week";
  const diff = now - before;
  if (diff === 0) return "Same as the week before";
  return `${diff > 0 ? "Up" : "Down"} ${Math.abs(diff)} from the week before`;
}

function Kpis({ m }: { m: Metrics }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        label="Prompts checked"
        value={formatNumber(m.prompts_checked)}
        note="Every message, before it is sent"
      />
      <KpiCard
        label="Handled without an AI model"
        value={formatPercent(m.zero_llm_share)}
        note="Fast checks, no tokens spent"
      />
      <KpiCard
        label="Incidents, last 7 days"
        value={formatNumber(m.incidents_7d)}
        note={change(m.incidents_7d, m.incidents_prev_7d)}
      />
      <KpiCard
        label="Unapproved AI tools in use"
        value={formatNumber(m.unapproved_tools)}
        note={
          <Link to="/security/tools" className="font-medium text-brand-700 underline">
            See which
          </Link>
        }
      />
    </div>
  );
}

function Recent({ page }: { page: IncidentPage }) {
  if (page.items.length === 0) return null;
  return (
    <section aria-labelledby="recent" className="mt-10">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="recent" className="text-lg font-semibold text-ink-900">
          Recent incidents
        </h2>
        <Link
          to="/security/incidents"
          className="inline-flex min-h-11 items-center rounded-lg bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Review all {formatNumber(page.total)} incidents
        </Link>
      </div>
      <ul className="mt-3 space-y-3">
        {page.items.map((i) => (
          <IncidentRow key={i.id} incident={i} />
        ))}
      </ul>
    </section>
  );
}

/** Container: loads the numbers and the latest incidents for the overview. */
export default function OverviewPage() {
  const [state, reload] = useFetch(load);

  if (state.status === "loading") {
    return (
      <div role="status" aria-label="Loading the overview" className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((n) => (
            <Skeleton key={n} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-32" />
      </div>
    );
  }
  if (state.status === "error") return <ErrorPanel what="the overview" onRetry={reload} />;

  const [metrics, page] = state.data;
  if (metrics.prompts_checked === 0 && page.total === 0) {
    return (
      <EmptyPanel title="Nothing checked yet">
        <p>
          Once someone sends a message, the numbers appear here.{" "}
          <Link to="/chat" className="font-medium text-brand-700 underline">
            Open Company Chat
          </Link>{" "}
          and send one to try it.
        </p>
      </EmptyPanel>
    );
  }
  return (
    <>
      {metrics.demo_data ? (
        <div className="mb-4 flex items-center gap-2 text-sm text-ink-600">
          <DemoBadge /> The people and numbers here are invented.
        </div>
      ) : null}
      <Kpis m={metrics} />
      <section
        aria-labelledby="ask-h"
        className="mt-10 rounded-lg border border-ink-200 bg-white p-4"
      >
        <h2 id="ask-h" className="text-lg font-semibold text-ink-900">
          Ask a question
        </h2>
        <p className="mt-1 max-w-prose text-ink-600">
          For example: which teams used unapproved AI tools and also had client data caught this
          week? You get a table and the SQL behind it.
        </p>
        <Link
          to="/security/ask"
          className="mt-3 inline-flex min-h-11 items-center rounded-lg px-1 text-sm font-semibold text-brand-700 underline"
        >
          Open the questions
        </Link>
      </section>
      <Recent page={page} />
    </>
  );
}
