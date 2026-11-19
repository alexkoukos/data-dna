import { RollingStat } from "@/components/ui/rolling-stat";
import { useState } from "react";
import { useLocation } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { fetchRecentIncidents, type Incident } from "../lib/securityApi";
import { useFetch } from "../lib/useFetch";
import { buildSeries, isSave, PERIODS, type Period } from "../lib/trends";
import { AnalyticsLineChart } from "@/components/ui/analytics-chart";
import { Skeleton } from "./ui";
import { Eye, EyeOff, RotateCw } from "lucide-react";

const KEY = "sentry.trends";
/** The trend is the point only on these pages; everywhere else the cards start folded. */
const OPEN_BY_DEFAULT = ["/security/impact", "/security/history"];

const SPAN: Record<Period, { short: string; long: string; unit: string }> = {
  Weekly: { short: "7 days", long: "the last 7 days", unit: "day" },
  Monthly: { short: "30 days", long: "the last 30 days", unit: "day" },
  Yearly: { short: "12 months", long: "the last 12 months", unit: "month" },
};

function readPref(): "show" | "hide" | null {
  try {
    const v = localStorage.getItem(KEY);
    return v === "show" || v === "hide" ? v : null;
  } catch {
    return null;
  }
}

function TrendCard({
  title,
  total,
  period,
  data,
  labels,
  dates,
  accent,
  gradient,
  unit,
}: {
  title: string;
  total: number;
  period: Period;
  data: number[];
  labels: string[];
  dates: string[];
  accent: string;
  gradient: { offset: string; color: string }[];
  unit: string;
}) {
  const peak = data.indexOf(Math.max(...data));
  const busiest =
    total > 0
      ? `Busiest ${SPAN[period].unit}: ${labels[peak]}, ${data[peak]}`
      : "Nothing in this period yet";
  return (
    <article className="min-w-0 rounded-lg border border-ink-200 bg-surface p-5">
      <h3 className="text-sm font-medium text-ink-600">{title}</h3>
      <p className="mt-1 flex flex-wrap items-baseline gap-x-2">
        <RollingStat value={total} className="text-4xl font-semibold tabular-nums text-ink-900" />
        <span className="text-sm text-ink-600">in {SPAN[period].long}</span>
      </p>
      <p className="mt-1 text-sm text-ink-600">{busiest}</p>
      <div className="mt-4">
        {/* The busiest day stays pinned; hover or touch any point for its day and count. */}
        <AnalyticsLineChart
          data={data.map((value, i) => ({ date: dates[i] ?? "", label: title, value }))}
          gradientStops={gradient}
          dotColors={data.map(() => accent)}
          gridLines={4}
          height={220}
          pinnedIndices={total > 0 ? [peak] : []}
          valueLabel={unit}
        />
        {/* The same numbers as a table for screen readers. A table ignores the 1 px width of
            sr-only and stretches the page on a phone, so the hidden box is a div that clips it. */}
        <div className="sr-only">
          <table>
            <caption>{`${title} per ${SPAN[period].unit}, ${SPAN[period].long}. ${total} in total.`}</caption>
            <tbody>
              {labels.map((l, i) => (
                <tr key={`${l}-${i}`}>
                  <th scope="row">{l}</th>
                  <td>{data[i] ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </article>
  );
}

function Cards({ incidents, period }: { incidents: Incident[]; period: Period }) {
  // "Now" is the newest incident, so invented demo data from an earlier day still draws a line.
  const end = new Date(Math.max(...incidents.map((i) => new Date(i.ts).getTime())));
  const all = buildSeries(incidents, period, end);
  const saved = buildSeries(incidents, period, end, isSave);
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <TrendCard
        title="Incidents"
        total={all.total}
        period={period}
        data={all.data}
        labels={all.labels}
        dates={all.dates}
        accent="#f59e0b"
        gradient={[
          { offset: "0%", color: "#f59e0b" },
          { offset: "100%", color: "#f97316" },
        ]}
        unit="caught"
      />
      <TrendCard
        title="Leaks stopped"
        total={saved.total}
        period={period}
        data={saved.data}
        labels={saved.labels}
        dates={saved.dates}
        accent="#30752a"
        gradient={[
          { offset: "0%", color: "#6fd36a" },
          { offset: "100%", color: "#30752a" },
        ]}
        unit="stopped"
      />
    </div>
  );
}

function Loaded({ period }: { period: Period }) {
  const [state, reload] = useFetch(fetchRecentIncidents);
  if (state.status === "loading")
    return (
      <div role="status" aria-label="Loading the trends" className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    );
  if (state.status === "error")
    return (
      <div
        role="status"
        className="rounded-lg border border-ink-200 bg-surface p-5 text-sm text-ink-700"
      >
        <p>I could not load the trends. Your other numbers are fine.</p>
        <TextureButton variant="secondary" type="button" onClick={reload} className="mt-3">
          <RotateCw className="size-4" aria-hidden="true" />
          Reload the trends
        </TextureButton>
      </div>
    );
  if (state.data.length === 0)
    return (
      <p className="rounded-lg border border-ink-200 bg-surface p-5 text-sm text-ink-700">
        No incidents yet. The trends appear after the first check.
      </p>
    );
  return <Cards incidents={state.data} period={period} />;
}

/** Two light trend cards (incidents, leaks stopped) on top of every security page. */
export function SecurityTrends() {
  const { pathname } = useLocation();
  const [pref, setPref] = useState(readPref);
  const [period, setPeriod] = useState<Period>("Weekly");
  const open = pref ? pref === "show" : OPEN_BY_DEFAULT.includes(pathname.replace(/\/$/, ""));
  const toggle = () => {
    const next = open ? "hide" : "show";
    setPref(next);
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* the choice still holds for this visit */
    }
  };
  return (
    <section aria-labelledby="trends-h" className="mb-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="trends-h" className="text-lg font-semibold text-ink-900">
          Trends
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          {open ? (
            <div role="group" aria-label="Period" className="flex gap-1">
              {PERIODS.map((p) => (
                <TextureButton
                  key={p}
                  type="button"
                  size="sm"
                  aria-pressed={p === period}
                  variant={p === period ? "primary" : "secondary"}
                  onClick={() => setPeriod(p)}
                >
                  {SPAN[p].short}
                </TextureButton>
              ))}
            </div>
          ) : null}
          <TextureButton
            type="button"
            size="sm"
            variant="minimal"
            onClick={toggle}
            aria-expanded={open}
          >
            {open ? (
              <EyeOff className="size-4" aria-hidden="true" />
            ) : (
              <Eye className="size-4" aria-hidden="true" />
            )}
            {open ? "Hide trends" : "Show trends"}
          </TextureButton>
        </div>
      </div>
      {open ? (
        <div className="mt-3">
          <Loaded period={period} />
        </div>
      ) : null}
    </section>
  );
}
