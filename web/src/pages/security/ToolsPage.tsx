import { useState } from "react";
import {
  ApprovalBadge,
  EmptyPanel,
  ErrorPanel,
  RiskLabel,
  Skeleton,
  Sparkline,
} from "../../components/ui";
import { formatNumber } from "../../lib/format";
import { fetchInventory, type Tool } from "../../lib/securityApi";
import { useFetch } from "../../lib/useFetch";

type Filter = "all" | Tool["approval"];
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "unapproved", label: "Unapproved" },
  { id: "tolerated", label: "Tolerated" },
  { id: "approved", label: "Approved" },
];
const ORDER = { unapproved: 0, tolerated: 1, approved: 2 } as const;

function ToolCard({ tool }: { tool: Tool }) {
  return (
    <li className="rounded-lg border border-ink-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-ink-900">{tool.name}</h3>
          <p className="text-sm text-ink-600">{tool.vendor ?? "Unknown vendor"}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <ApprovalBadge approval={tool.approval} />
          <RiskLabel risk={tool.risk} />
        </div>
      </div>
      {tool.reason ? <p className="mt-2 max-w-prose text-sm text-ink-700">{tool.reason}</p> : null}
      {tool.alternative && tool.approval !== "approved" ? (
        <p className="mt-1 text-sm font-medium text-ink-900">Use {tool.alternative} instead.</p>
      ) : null}
      <dl className="mt-3 flex flex-wrap items-end gap-x-8 gap-y-2 text-sm text-ink-600">
        <div>
          <dt>Requests, 14 days</dt>
          <dd className="text-lg font-semibold tabular-nums text-ink-900">
            {formatNumber(tool.requests)}
          </dd>
        </div>
        <div>
          <dt>Most people in one day</dt>
          <dd className="text-lg font-semibold tabular-nums text-ink-900">
            {formatNumber(tool.peak_users)}
          </dd>
        </div>
        <div>
          <dt>Teams</dt>
          <dd className="font-medium text-ink-900">
            {tool.teams.length > 0 ? tool.teams.join(", ") : "None seen"}
          </dd>
        </div>
        <div>
          <dt>Last 7 days</dt>
          <dd>
            <Sparkline values={tool.trend} />
          </dd>
        </div>
        {tool.first_seen ? (
          <div>
            <dt>First seen</dt>
            <dd className="font-medium text-ink-900">{tool.first_seen}</dd>
          </div>
        ) : null}
      </dl>
    </li>
  );
}

/** Container: the AI tool inventory, unapproved tools first, with a filter by approval. */
export default function ToolsPage() {
  const [state, reload] = useFetch(fetchInventory);
  const [filter, setFilter] = useState<Filter>("all");

  if (state.status === "loading") {
    return (
      <div role="status" aria-label="Loading AI tools" className="space-y-3">
        {[0, 1, 2].map((n) => (
          <Skeleton key={n} className="h-32" />
        ))}
      </div>
    );
  }
  if (state.status === "error") return <ErrorPanel what="the AI tools" onRetry={reload} />;

  const tools = state.data;
  if (tools.length === 0) {
    return (
      <EmptyPanel title="No AI tools yet">
        <p>The list appears once the first network logs are read.</p>
      </EmptyPanel>
    );
  }
  const count = (f: Filter) =>
    f === "all" ? tools.length : tools.filter((t) => t.approval === f).length;
  const shown = tools
    .filter((t) => filter === "all" || t.approval === filter)
    .sort((a, b) => ORDER[a.approval] - ORDER[b.approval] || b.requests - a.requests);

  return (
    <>
      <p className="max-w-prose text-ink-600">
        Every AI tool we can see in network logs and gate traffic. Unapproved tools come first.
      </p>
      <div role="group" aria-label="Filter by approval" className="mt-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={`min-h-11 rounded-md border px-3 text-sm font-medium ${filter === f.id ? "border-brand-600 bg-brand-50 text-brand-700" : "border-ink-300 bg-white text-ink-700 hover:bg-ink-100"}`}
          >
            {f.label} ({count(f.id)})
          </button>
        ))}
      </div>
      {shown.length === 0 ? (
        <div className="mt-4">
          <EmptyPanel title="Nothing in this group">
            <p>No tool matches this filter. Choose All to see everything.</p>
          </EmptyPanel>
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {shown.map((t) => (
            <ToolCard key={t.id} tool={t} />
          ))}
        </ul>
      )}
    </>
  );
}
