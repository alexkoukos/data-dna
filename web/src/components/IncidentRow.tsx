import { Link } from "react-router-dom";
import { explainReason } from "../lib/explain";
import { formatDateTime } from "../lib/format";
import type { Incident } from "../lib/securityApi";
import { OutcomeChip } from "./OutcomeChip";

/** Same columns for the header and every row, so they line up. */
const COLUMNS = "md:grid-cols-[11rem_7.5rem_minmax(0,1fr)_7rem_6.5rem_10rem]";

/** Presentational: the column names above the incident rows. Hidden on phones, where rows wrap. */
export function IncidentHeader() {
  return (
    <div
      aria-hidden="true"
      className={`hidden gap-x-4 px-4 pb-2 text-xs font-semibold uppercase tracking-wide text-ink-600 md:grid ${COLUMNS}`}
    >
      <span>Outcome</span>
      <span>When</span>
      <span>What happened</span>
      <span>Team</span>
      <span>Person</span>
      <span>Tool</span>
    </div>
  );
}

/** Presentational: one incident as a 48 px row. Details open on click. No raw prompt is ever shown,
 * only the masked preview. */
export function IncidentRow({ incident }: { incident: Incident }) {
  const summary = incident.reasons[0] ? explainReason(incident.reasons[0]) : "Flagged by policy.";
  const team = incident.team ?? "Unknown";
  const tool = incident.tool ?? "Unknown";
  return (
    <li className="border-b border-ink-200 bg-white first:rounded-t-lg last:rounded-b-lg last:border-b-0">
      <details className="group">
        <summary
          className={`grid min-h-12 cursor-pointer list-none items-center gap-x-4 gap-y-1 px-4 py-2 hover:bg-ink-50 max-md:grid-cols-[auto_1fr] [&::-webkit-details-marker]:hidden ${COLUMNS}`}
        >
          <span className="justify-self-start">
            <OutcomeChip outcome={incident.decision} />
          </span>
          <time dateTime={incident.ts} className="text-sm text-ink-600 max-md:justify-self-end">
            {formatDateTime(incident.ts)}
          </time>
          <span className="min-w-0 text-sm font-medium text-ink-900 max-md:col-span-2 md:truncate">
            {summary}
          </span>
          <span className="truncate text-sm text-ink-700" title={team}>
            {team}
          </span>
          <span className="truncate text-sm text-ink-700" title={incident.user}>
            {incident.user}
          </span>
          <span className="truncate text-sm text-ink-700" title={tool}>
            {tool}
          </span>
        </summary>
        <div className="space-y-2 border-t border-ink-100 bg-ink-50 px-4 py-3 text-sm">
          {incident.reasons.slice(1).map((r) => (
            <p key={r} className="text-ink-700">
              {explainReason(r)}
            </p>
          ))}
          {incident.masked_preview ? (
            <p className="text-ink-600">
              Seen, masked:{" "}
              <span className="break-all font-mono text-ink-900">{incident.masked_preview}</span>
            </p>
          ) : null}
          <Link
            to={`/security/incidents/${incident.id}`}
            aria-label={`Open details of incident ${incident.id}`}
            className="inline-flex min-h-11 items-center rounded-md border border-ink-300 bg-white px-4 text-sm font-semibold text-ink-900 hover:bg-ink-100"
          >
            Open details
          </Link>
        </div>
      </details>
    </li>
  );
}
