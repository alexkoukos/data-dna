import { Link, useParams } from "react-router-dom";
import { OutcomeChip } from "../../components/OutcomeChip";
import { SealedIdentity } from "../../components/SealedIdentity";
import { ErrorPanel, Skeleton } from "../../components/ui";
import { explainReason } from "../../lib/explain";
import { formatDateTime } from "../../lib/format";
import { fetchIncidentDetail } from "../../lib/securityApi";
import { useFetch } from "../../lib/useFetch";

const WHAT_WE_DID = {
  allow: "The message went through unchanged.",
  mask: "The sensitive value was replaced by a placeholder before it left the company.",
  local: "A model inside the company answered, so the data did not leave.",
  warn: "The sender was stopped and asked before sending.",
  block: "The message was not sent.",
} as const;

/** Container: one incident with what was found, the document match, the timeline and the sealed
 * identity flow. Never shows the raw prompt. */
function Detail({ id }: { id: string }) {
  const [state, reload] = useFetch(() => fetchIncidentDetail(id));

  if (state.status === "loading") {
    return (
      <div role="status" aria-label="Loading the incident" className="space-y-3">
        <Skeleton className="h-32" />
        <Skeleton className="h-48" />
      </div>
    );
  }
  if (state.status === "error") return <ErrorPanel what="this incident" onRetry={reload} />;

  const { incident, document, copy_code, timeline, reveals } = state.data;
  return (
    <div className="space-y-6">
      <section aria-labelledby="what-h" className="rounded-2xl border border-ink-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <OutcomeChip outcome={incident.decision} />
          <time dateTime={incident.ts} className="text-sm text-ink-600">
            {formatDateTime(incident.ts)}
          </time>
        </div>
        <h2 id="what-h" className="mt-2 text-lg font-semibold text-ink-900">
          What happened
        </h2>
        {incident.reasons.map((r) => (
          <p key={r} className="text-ink-900">
            {explainReason(r)}
          </p>
        ))}
        <p className="mt-2 text-ink-700">{WHAT_WE_DID[incident.decision]}</p>
        <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2 text-sm text-ink-600">
          <div>
            <dt>Team</dt>
            <dd className="font-medium text-ink-900">{incident.team ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Tool</dt>
            <dd className="font-medium text-ink-900">{incident.tool ?? "Unknown"}</dd>
          </div>
          {incident.masked_preview ? (
            <div>
              <dt>What was seen, masked</dt>
              <dd className="break-all font-mono text-ink-900">{incident.masked_preview}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      <section aria-labelledby="doc-h" className="rounded-2xl border border-ink-200 bg-white p-4">
        <h2 id="doc-h" className="text-lg font-semibold text-ink-900">
          Document match
        </h2>
        {document ? (
          <p className="mt-1 text-ink-900">
            Matches <span className="font-semibold">{document.title}</span> ({document.sensitivity})
            {incident.score !== null ? `, similarity ${Math.round(incident.score * 100)}%` : ""}.
          </p>
        ) : (
          <p className="mt-1 text-ink-700">No protected document was involved.</p>
        )}
        <p className="mt-1 text-ink-700">
          {copy_code
            ? `Marked copy ${copy_code}: this points to the person who received that copy.`
            : "No marked copy was involved, so there is no copy to trace."}
        </p>
      </section>

      <SealedIdentity
        key={`${incident.id}-${reveals[0]?.status ?? "none"}`}
        incidentId={incident.id}
        pseudonym={incident.user}
        latest={reveals[0]}
        onChanged={reload}
      />

      <section aria-labelledby="line-h">
        <h2 id="line-h" className="text-lg font-semibold text-ink-900">
          Other incidents from {incident.user}
        </h2>
        {timeline.length === 0 ? (
          <p className="mt-1 text-ink-700">This is the only incident from this person.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {timeline.map((t) => (
              <li
                key={t.id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-ink-200 bg-white p-3"
              >
                <OutcomeChip outcome={t.decision} />
                <time dateTime={t.ts} className="text-sm text-ink-600">
                  {formatDateTime(t.ts)}
                </time>
                <Link
                  to={`/security/incidents/${t.id}`}
                  className="inline-flex min-h-11 items-center text-sm font-semibold text-brand-700 underline"
                >
                  {t.reasons[0] ? explainReason(t.reasons[0]) : "Open incident"}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default function IncidentDetailPage() {
  const { id = "" } = useParams();
  return (
    <>
      <Link
        to="/security/incidents"
        className="mb-4 inline-flex min-h-11 items-center text-sm font-semibold text-brand-700 underline"
      >
        All incidents
      </Link>
      <Detail key={id} id={id} />
    </>
  );
}
