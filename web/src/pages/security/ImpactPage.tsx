import { ErrorPanel, Skeleton } from "../../components/ui";
import {
  fetchCoaching,
  fetchRoi,
  fetchWeekly,
  type CoachingStats,
  type Roi,
  type WeeklySummary,
} from "../../lib/securityApi";
import { useFetch } from "../../lib/useFetch";

const eur = new Intl.NumberFormat("en", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-lg border border-ink-200 bg-surface p-4">
      <dt className="text-sm text-ink-600">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold text-ink-900">{value}</dd>
      {note ? <p className="mt-1 text-xs text-ink-600">{note}</p> : null}
    </div>
  );
}

function Weekly({ data }: { data: WeeklySummary }) {
  return (
    <section aria-labelledby="weekly-h" className="rounded-lg border border-ink-200 bg-surface p-4">
      <h2 id="weekly-h" className="text-lg font-semibold text-ink-900">
        This week for the CISO
      </h2>
      <p className="mt-1 font-medium text-ink-900">{data.headline}</p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-700">
        {data.lines.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>
    </section>
  );
}

function RoiView({ roi, coaching }: { roi: Roi; coaching: CoachingStats }) {
  const cats = Object.entries(roi.by_category);
  return (
    <>
      <dl className="grid gap-3 sm:grid-cols-3">
        <Stat label={`Leaks stopped, last ${roi.days} days`} value={String(roi.leaks_stopped)} />
        <Stat
          label="Estimated cost avoided"
          value={eur.format(roi.cost_avoided_eur)}
          note={`An estimate: ${Math.round(roi.assumptions.likelihood * 100)}% of the ${eur.format(roi.exposure_eur)} exposure.`}
        />
        <Stat
          label="Safer rewrites taken"
          value={coaching.shown ? `${Math.round(coaching.acceptance_rate * 100)}%` : "None yet"}
          note={`${coaching.accepted} of ${coaching.shown} warnings`}
        />
      </dl>
      {roi.would_have_stopped > 0 ? (
        <p className="text-sm text-ink-700">
          Shadow mode would also have stopped {roi.would_have_stopped} more.
        </p>
      ) : null}

      <section aria-labelledby="cats-h">
        <h2 id="cats-h" className="text-lg font-semibold text-ink-900">
          What was stopped
        </h2>
        {cats.length === 0 ? (
          <p className="text-sm text-ink-700">Nothing was stopped in this period.</p>
        ) : (
          <ul className="mt-2 flex flex-wrap gap-2">
            {cats.map(([c, n]) => (
              <li key={c} className="rounded-sm bg-ink-100 px-3 py-1 text-sm text-ink-900">
                {c.replace(/_/g, " ")} <span className="font-semibold">{n}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="risk-h">
        <h2 id="risk-h" className="text-lg font-semibold text-ink-900">
          Risk per tool
        </h2>
        <div className="mt-2 overflow-x-auto rounded-lg border border-ink-200 bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-50 text-ink-700">
              <tr>
                <th scope="col" className="px-3 py-2">
                  Tool
                </th>
                <th scope="col" className="px-3 py-2">
                  Approval
                </th>
                <th scope="col" className="px-3 py-2">
                  Risk
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Requests
                </th>
                <th scope="col" className="px-3 py-2 text-right">
                  Risk score
                </th>
              </tr>
            </thead>
            <tbody>
              {roi.tools.map((t) => (
                <tr key={t.name} className="border-t border-ink-200">
                  <th scope="row" className="px-3 py-2 font-medium text-ink-900">
                    {t.name}
                  </th>
                  <td className="px-3 py-2">{t.approval}</td>
                  <td className="px-3 py-2">{t.risk}</td>
                  <td className="px-3 py-2 text-right">{t.requests}</td>
                  <td className="px-3 py-2 text-right font-semibold">{t.risk_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 max-w-prose text-xs text-ink-600">
          Risk score is the tool&apos;s risk weight times its requests. It ranks where to look
          first; it is not a probability.
        </p>
      </section>

      <details className="rounded-lg border border-ink-200 bg-surface p-4">
        <summary className="cursor-pointer text-sm font-semibold text-ink-900">
          How the estimate is made
        </summary>
        <p className="mt-2 max-w-prose text-sm text-ink-700">
          {roi.assumptions.note} Each stopped leak counts once, at the cost of the most expensive
          thing in it.
        </p>
        <ul className="mt-2 grid gap-x-6 text-sm text-ink-700 sm:grid-cols-2">
          {Object.entries(roi.assumptions.unit_cost_eur).map(([k, v]) => (
            <li key={k}>
              {k.replace(/_/g, " ")}: {eur.format(v)}
            </li>
          ))}
          {Object.entries(roi.assumptions.document_cost_eur).map(([k, v]) => (
            <li key={k}>
              {k} document: {eur.format(v)}
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}

export default function ImpactPage() {
  const [roi, reloadRoi] = useFetch(fetchRoi);
  const [weekly] = useFetch(fetchWeekly);
  const [coaching] = useFetch(fetchCoaching);

  if (roi.status === "loading") {
    return <Skeleton className="h-48" aria-label="Loading impact" />;
  }
  if (roi.status === "error") return <ErrorPanel what="the impact numbers" onRetry={reloadRoi} />;
  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold text-ink-900">Impact</h2>
        <p className="max-w-prose text-ink-700">
          What the gate stopped, and what that is worth. Estimates, with the assumptions shown.
        </p>
      </header>
      {weekly.status === "ready" ? <Weekly data={weekly.data} /> : null}
      <RoiView
        roi={roi.data}
        coaching={
          coaching.status === "ready"
            ? coaching.data
            : { shown: 0, accepted: 0, acceptance_rate: 0 }
        }
      />
    </div>
  );
}
