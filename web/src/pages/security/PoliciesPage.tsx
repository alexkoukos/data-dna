import { useState } from "react";
import { ShadowCard } from "../../components/ShadowCard";
import { OutcomeChip } from "../../components/OutcomeChip";
import { EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import { ACTIONS, EFFECT, textFor } from "../../lib/policyText";
import {
  COMPLIANCE_REPORT_URL,
  fetchPolicies,
  fetchShadow,
  savePolicy,
  saveShadow,
  type Decision,
  type Policy,
  type ShadowStatus,
} from "../../lib/securityApi";
import { useFetch } from "../../lib/useFetch";

function PolicyRow({ policy, onSaved }: { policy: Policy; onSaved: (p: Policy) => void }) {
  const [draft, setDraft] = useState<Decision>(policy.action);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const text = textFor(policy.scope, policy.key);
  const id = `${policy.scope}-${policy.key}`;
  const changed = draft !== policy.action;

  async function save() {
    setSaving(true);
    setError(null);
    try {
      onSaved(await savePolicy(policy.scope, policy.key, draft));
    } catch (e) {
      setError(e instanceof Error ? e.message : "The change was not saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className="rounded-lg border border-ink-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-ink-900">{text.label}</h3>
          <p className="text-sm text-ink-600">{text.about}</p>
        </div>
        <OutcomeChip outcome={policy.action} />
      </div>
      <div className="mt-3">
        <label htmlFor={id} className="block text-sm font-medium text-ink-700">
          What happens to {text.label.toLowerCase()}
        </label>
        <select
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value as Decision)}
          className="mt-1 min-h-11 w-full max-w-xs rounded-md border border-ink-300 bg-white px-3 text-sm text-ink-900"
        >
          {ACTIONS.map((a) => (
            <option key={a.id} value={a.id}>
              {a.label}
            </option>
          ))}
        </select>
      </div>
      <p className="mt-2 max-w-prose text-sm text-ink-700">
        {changed ? "If you save: " : "Today: "}
        {EFFECT[draft]}
      </p>
      {changed && draft === "allow" ? (
        <p className="mt-1 max-w-prose text-sm font-semibold text-warn-fg">
          Nothing will be checked for this any more.
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-2 text-sm font-semibold text-block-fg">
          {error}
        </p>
      ) : null}
      {changed ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={save}
            disabled={saving}
            className="min-h-11 rounded-md bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-ink-200 disabled:text-ink-700"
          >
            {saving ? "Saving…" : `Save ${text.label.toLowerCase()}`}
          </button>
          <button
            type="button"
            onClick={() => {
              setDraft(policy.action);
              setError(null);
            }}
            className="min-h-11 rounded-md px-4 text-sm font-medium text-ink-700 hover:bg-ink-100"
          >
            Cancel
          </button>
        </div>
      ) : null}
      {policy.updated_by && policy.updated_at ? (
        <p className="mt-2 text-xs text-ink-600">
          Last changed by {policy.updated_by} on {policy.updated_at.slice(0, 10)}.
        </p>
      ) : null}
    </li>
  );
}

function Group({
  title,
  policies,
  onSaved,
}: {
  title: string;
  policies: Policy[];
  onSaved: (p: Policy) => void;
}) {
  if (policies.length === 0) return null;
  return (
    <section aria-label={title} className="mt-6">
      <h2 className="text-lg font-semibold text-ink-900">{title}</h2>
      <ul className="mt-3 space-y-3">
        {policies.map((p) => (
          <PolicyRow key={`${p.scope}-${p.key}`} policy={p} onSaved={onSaved} />
        ))}
      </ul>
    </section>
  );
}

function Shadow() {
  const [state] = useFetch(fetchShadow);
  const [override, setOverride] = useState<ShadowStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status = override ?? (state.status === "ready" ? state.data : null);
  if (status === null) return null;
  async function toggle(next: boolean) {
    setBusy(true);
    setError(null);
    try {
      setOverride(await saveShadow(next));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Shadow mode was not changed.");
    } finally {
      setBusy(false);
    }
  }
  return <ShadowCard status={status} busy={busy} error={error} onToggle={toggle} />;
}

function ReportCard() {
  return (
    <section
      aria-labelledby="report-h"
      className="mt-4 rounded-lg border border-ink-200 bg-white p-4"
    >
      <h2 id="report-h" className="text-lg font-semibold text-ink-900">
        Compliance report
      </h2>
      <p className="max-w-prose text-sm text-ink-700">
        A PDF that maps what the gate does to GDPR, NIS2 and the EU AI Act, with the live numbers.
        It supports your own review; it is not legal advice.
      </p>
      <a
        href={COMPLIANCE_REPORT_URL}
        download
        className="mt-3 inline-flex min-h-11 items-center rounded-md border border-ink-300 px-4 text-sm font-semibold text-ink-900 hover:bg-ink-100"
      >
        Download the PDF report
      </a>
    </section>
  );
}

/** Container: what the gate does for each kind of sensitive data. Edits apply within seconds. */
export default function PoliciesPage() {
  const [state, reload] = useFetch(fetchPolicies);
  const [saved, setSaved] = useState<Policy[]>([]);

  if (state.status === "loading") {
    return (
      <div role="status" aria-label="Loading policies" className="space-y-3">
        {[0, 1, 2, 3].map((n) => (
          <Skeleton key={n} className="h-32" />
        ))}
      </div>
    );
  }
  if (state.status === "error") return <ErrorPanel what="the policies" onRetry={reload} />;
  if (state.data.length === 0) {
    return (
      <EmptyPanel title="No policies yet">
        <p>Policies are created when the service starts. Restart it and check again.</p>
      </EmptyPanel>
    );
  }

  const merged = state.data.map(
    (p) => saved.find((s) => s.scope === p.scope && s.key === p.key) ?? p,
  );
  const onSaved = (p: Policy) => setSaved((prev) => [...prev, p]);
  return (
    <>
      <p className="max-w-prose text-ink-600">
        Choose what happens when the gate finds each kind of data. When several apply to one
        message, the strictest wins: block, then answer locally, then warn, then mask.
      </p>
      <Shadow />
      <ReportCard />
      <Group
        title="Sensitive data"
        policies={merged.filter((p) => p.scope === "category")}
        onSaved={onSaved}
      />
      <Group
        title="Documents"
        policies={merged.filter((p) => p.scope === "sensitivity")}
        onSaved={onSaved}
      />
    </>
  );
}
