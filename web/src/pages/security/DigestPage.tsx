import { useState } from "react";
import { EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import {
  fetchDigest,
  fetchDigestTeams,
  markdownUrl,
  trendText,
  type Digest,
} from "../../lib/digestApi";
import { useFetch } from "../../lib/useFetch";

const LABEL: Record<string, string> = {
  allow: "Allowed",
  mask: "Masked",
  warn: "Warned",
  local: "Answered locally",
  block: "Blocked",
  rerouted: "Sent to Company AI",
};

function DigestView({ team }: { team: string }) {
  const [state, reload] = useFetch(() => fetchDigest(team));
  const [copied, setCopied] = useState<"idle" | "done" | "manual">("idle");

  if (state.status === "loading") return <Skeleton className="h-48 w-full" />;
  if (state.status === "error") return <ErrorPanel what="the digest" onRetry={reload} />;
  const d: Digest = state.data;

  async function copy() {
    const text = `Subject: ${d.email.subject}\n\n${d.email.body}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied("done");
    } catch {
      // Clipboard can be blocked: show the text so it can be selected by hand.
      setCopied("manual");
    }
  }

  return (
    <article aria-label={`Digest for ${d.team}`} className="mt-4">
      <p className="rounded-lg border border-brand-600/30 bg-brand-50 p-3 text-sm text-ink-900">
        {d.note}
      </p>
      <h2 className="mt-4 text-xl font-semibold text-ink-900">{d.team}</h2>
      <p className="text-sm text-ink-600">
        {d.start ? `${d.start} to ${d.end}` : "No activity recorded yet"}
      </p>
      <p className="mt-2 text-lg text-ink-900">{trendText(d)}</p>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <section aria-label="Outcomes">
          <h3 className="text-sm font-semibold text-ink-900">Outcomes</h3>
          {Object.keys(d.outcomes).length === 0 ? (
            <p className="mt-1 text-sm text-ink-600">Nothing was stopped this week.</p>
          ) : (
            <ul className="mt-1 divide-y divide-ink-100 rounded-lg border border-ink-200 bg-surface">
              {Object.entries(d.outcomes).map(([k, n]) => (
                <li key={k} className="flex justify-between px-3 py-2 text-sm">
                  <span>{LABEL[k] ?? k}</span>
                  <span className="font-semibold tabular-nums">{n}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section aria-label="Kinds of data">
          <h3 className="text-sm font-semibold text-ink-900">Kinds of data</h3>
          {d.categories.length === 0 ? (
            <p className="mt-1 text-sm text-ink-600">No sensitive data was found.</p>
          ) : (
            <ul className="mt-1 divide-y divide-ink-100 rounded-lg border border-ink-200 bg-surface">
              {d.categories.map((c) => (
                <li key={c.category} className="flex justify-between px-3 py-2 text-sm">
                  <span>{c.category.replace(/_/g, " ")}</span>
                  <span className="font-semibold tabular-nums">{c.count}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section aria-label="Tools" className="mt-4">
        <h3 className="text-sm font-semibold text-ink-900">Tools</h3>
        {d.tools.length === 0 ? (
          <p className="mt-1 text-sm text-ink-600">No tool was involved in an incident.</p>
        ) : (
          <ul className="mt-1 divide-y divide-ink-100 rounded-lg border border-ink-200 bg-surface">
            {d.tools.map((t) => (
              <li key={t.name} className="flex flex-wrap justify-between gap-2 px-3 py-2 text-sm">
                <span>
                  {t.name} <span className="text-ink-600">({t.approval})</span>
                </span>
                <span className="font-semibold tabular-nums">{t.count}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Do this instead" className="mt-4">
        <h3 className="text-sm font-semibold text-ink-900">Do this instead</h3>
        <ul className="mt-1 list-disc space-y-1 pl-5 text-ink-900">
          {d.tips.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </section>

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => void copy()}
          className="min-h-11 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-[#04141a] hover:bg-brand-700"
        >
          Copy as email
        </button>
        <a
          href={markdownUrl(d.team)}
          download
          className="inline-flex min-h-11 items-center rounded-lg border border-ink-300 bg-surface px-5 text-sm font-semibold text-ink-900 hover:bg-ink-100"
        >
          Download Markdown
        </a>
      </div>
      {copied === "done" ? (
        <p role="status" className="mt-2 text-sm text-allow-fg">
          Copied. Paste it into an email. Nothing was sent.
        </p>
      ) : null}
      {copied === "manual" ? (
        <div className="mt-2">
          <label htmlFor="email-draft" className="text-sm text-ink-700">
            Your browser blocked copying. Select and copy the text below.
          </label>
          <textarea
            id="email-draft"
            readOnly
            rows={10}
            value={`Subject: ${d.email.subject}\n\n${d.email.body}`}
            className="mt-1 w-full rounded-lg border border-ink-300 bg-surface p-3 text-sm"
          />
        </div>
      ) : null}
    </article>
  );
}

/** Security: one weekly digest per team lead. Team-level counts only, nothing is emailed. */
export default function DigestPage() {
  const [state, reload] = useFetch(fetchDigestTeams);
  const [picked, setPicked] = useState("");
  // The first team until the person picks one: derived while rendering, not set in an effect.
  const team = picked || (state.status === "ready" ? (state.data[0] ?? "") : "");

  return (
    <section aria-label="Weekly digest">
      <h2 className="text-lg font-semibold text-ink-900">Weekly team digest</h2>
      <p className="mt-1 max-w-prose text-ink-600">
        One page per team lead: what was stopped this week, how it compares with last week, and what
        to do instead. It teaches the team instead of only blocking it.
      </p>
      {state.status === "loading" ? <Skeleton className="mt-4 h-12 w-full" /> : null}
      {state.status === "error" ? (
        <div className="mt-4">
          <ErrorPanel what="the teams" onRetry={reload} />
        </div>
      ) : null}
      {state.status === "ready" && state.data.length === 0 ? (
        <div className="mt-4">
          <EmptyPanel title="No digest yet">
            <p>A digest appears once a team has had its first incident.</p>
          </EmptyPanel>
        </div>
      ) : null}
      {state.status === "ready" && state.data.length > 0 ? (
        <>
          <label htmlFor="digest-team" className="mt-4 block text-sm font-semibold text-ink-900">
            Team
          </label>
          <select
            id="digest-team"
            value={team}
            onChange={(e) => setPicked(e.target.value)}
            className="mt-1 min-h-11 w-full rounded-lg border border-ink-300 bg-surface px-3 sm:w-72"
          >
            {state.data.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          {team ? <DigestView key={team} team={team} /> : null}
        </>
      ) : null}
    </section>
  );
}
