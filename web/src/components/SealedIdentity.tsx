import { useState } from "react";
import { decideReveal, fetchIdentity, requestReveal, type Reveal } from "../lib/securityApi";

const field =
  "mt-1 min-h-11 w-full rounded-lg border border-ink-300 bg-white px-3 text-sm text-ink-900";
const primary =
  "min-h-11 rounded-lg bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60";
const quiet = "min-h-11 rounded-lg px-4 text-sm font-medium text-ink-700 hover:bg-ink-100";

interface Props {
  incidentId: number;
  pseudonym: string;
  latest: Reveal | undefined;
  onChanged: () => void;
}

/** The person behind an incident is sealed. One person asks, a different person approves. */
export function SealedIdentity({ incidentId, pseudonym, latest, onChanged }: Props) {
  const [name, setName] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [realName, setRealName] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not work. Nothing was changed.");
    } finally {
      setBusy(false);
    }
  }

  async function show(request: Reveal) {
    setBusy(true);
    setError(null);
    try {
      const who = await fetchIdentity(incidentId, request.id, name || request.requested_by);
      setRealName(who.display_name ?? "No name on file");
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not work.");
    } finally {
      setBusy(false);
    }
  }

  const status = latest?.status;
  return (
    <section aria-labelledby="who-h" className="rounded-lg border border-ink-200 bg-white p-4">
      <h2 id="who-h" className="text-lg font-semibold text-ink-900">
        Who
      </h2>
      <p className="mt-1 text-ink-700">
        Pseudonym <span className="font-mono font-semibold text-ink-900">{pseudonym}</span>. The
        real name stays sealed. It opens only when one person asks with a reason and a different
        person approves. Every step is logged.
      </p>

      {realName ? (
        <p role="status" className="mt-3 rounded-lg bg-mask-bg p-3 font-semibold text-mask-fg">
          Real name: {realName}. This view was logged.
        </p>
      ) : null}

      {status === "pending" && latest ? (
        <div className="mt-4">
          <p role="status" className="font-semibold text-ink-900">
            Waiting for a second person. {latest.requested_by} asked: {latest.reason}
          </p>
          <label className="mt-3 block text-sm font-medium text-ink-700">
            Your name
            <input value={name} onChange={(e) => setName(e.target.value)} className={field} />
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy || !name.trim()}
              onClick={() => run(() => decideReveal(latest.id, name, true))}
              className={primary}
            >
              Approve the reveal
            </button>
            <button
              type="button"
              disabled={busy || !name.trim()}
              onClick={() => run(() => decideReveal(latest.id, name, false))}
              className={quiet}
            >
              Deny
            </button>
          </div>
        </div>
      ) : null}

      {status === "approved" && latest && !realName ? (
        <div className="mt-4">
          <p className="text-ink-700">
            Approved by {latest.approved_by}. Enter your name so the view is logged under it.
          </p>
          <label className="mt-3 block text-sm font-medium text-ink-700">
            Your name
            <input value={name} onChange={(e) => setName(e.target.value)} className={field} />
          </label>
          <button
            type="button"
            disabled={busy || !name.trim()}
            onClick={() => show(latest)}
            className={`${primary} mt-3`}
          >
            Show the real name
          </button>
        </div>
      ) : null}

      {status !== "pending" && status !== "approved" ? (
        <form
          className="mt-4"
          onSubmit={(e) => {
            e.preventDefault();
            void run(() => requestReveal(incidentId, name, reason));
          }}
        >
          {status === "denied" ? (
            <p className="mb-3 text-sm text-ink-700">The last request was denied.</p>
          ) : null}
          <label className="block text-sm font-medium text-ink-700">
            Your name
            <input value={name} onChange={(e) => setName(e.target.value)} className={field} />
          </label>
          <label className="mt-3 block text-sm font-medium text-ink-700">
            Why do you need to know who this is? (at least 10 characters)
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className={`${field} py-2`}
            />
          </label>
          <button
            type="submit"
            disabled={busy || !name.trim() || reason.trim().length < 10}
            className={`${primary} mt-3`}
          >
            Request reveal
          </button>
        </form>
      ) : null}

      {error ? (
        <p role="alert" className="mt-3 text-sm font-semibold text-block-fg">
          {error}
        </p>
      ) : null}
    </section>
  );
}
