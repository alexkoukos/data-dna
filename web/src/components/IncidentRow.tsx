import { explainReason } from "../lib/explain";
import { formatDateTime } from "../lib/format";
import type { Incident } from "../lib/securityApi";
import { OutcomeChip } from "./OutcomeChip";

/** Presentational: one incident. No raw prompt is ever shown, only the masked preview. */
export function IncidentRow({ incident }: { incident: Incident }) {
  return (
    <li className="rounded-2xl border border-ink-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <OutcomeChip outcome={incident.decision} />
        <time dateTime={incident.ts} className="text-sm text-ink-600">
          {formatDateTime(incident.ts)}
        </time>
      </div>
      <p className="mt-2 text-base font-medium text-ink-900">
        {incident.reasons[0] ? explainReason(incident.reasons[0]) : "Flagged by policy."}
      </p>
      {incident.reasons.slice(1).map((r) => (
        <p key={r} className="text-sm text-ink-700">
          {explainReason(r)}
        </p>
      ))}
      <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm text-ink-600">
        <div className="flex gap-1">
          <dt>Team</dt>
          <dd className="font-medium text-ink-900">{incident.team ?? "Unknown"}</dd>
        </div>
        <div className="flex gap-1">
          <dt>Person</dt>
          <dd className="font-medium text-ink-900">{incident.user}</dd>
        </div>
        <div className="flex gap-1">
          <dt>Tool</dt>
          <dd className="font-medium text-ink-900">{incident.tool ?? "Unknown"}</dd>
        </div>
        {incident.masked_preview ? (
          <div className="flex gap-1">
            <dt>Seen</dt>
            <dd className="font-mono text-ink-900">{incident.masked_preview}</dd>
          </div>
        ) : null}
      </dl>
    </li>
  );
}
