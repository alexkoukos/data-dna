import { useState, type FormEvent } from "react";
import { OutcomeChip } from "../../components/OutcomeChip";
import { EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import { ACTIONS } from "../../lib/policyText";
import {
  fetchGroupPolicies,
  deleteGroupPolicy,
  saveGroupPolicy,
  type Decision,
  type GroupPolicy,
} from "../../lib/securityApi";
import { useFetch } from "../../lib/useFetch";

const CATEGORIES = [
  "greek_id",
  "iban",
  "card",
  "secret",
  "person_email_phone",
  "client_name",
  "source_code",
];
const SENSITIVITIES = ["internal", "confidential", "restricted"];

/** Container: exceptions to the company policy for one team or one role. Role wins over team. */
export default function GroupsPage() {
  const [state, reload] = useFetch(fetchGroupPolicies);
  const [items, setItems] = useState<GroupPolicy[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<GroupPolicy>({
    kind: "team",
    group: "",
    scope: "category",
    key: "client_name",
    action: "allow",
  });

  if (state.status === "loading") {
    return (
      <div role="status" aria-label="Loading group policies">
        <Skeleton className="h-32" />
      </div>
    );
  }
  if (state.status === "error") return <ErrorPanel what="the group policies" onRetry={reload} />;
  const list = items ?? state.data;

  async function run(fn: () => Promise<GroupPolicy[]>) {
    setError(null);
    try {
      setItems(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "The change was not saved.");
    }
  }
  function add(e: FormEvent) {
    e.preventDefault();
    if (!draft.group.trim()) {
      setError("Say which team or role this applies to.");
      return;
    }
    void run(() => saveGroupPolicy({ ...draft, group: draft.group.trim() }));
  }
  const keys = draft.scope === "category" ? CATEGORIES : SENSITIVITIES;
  const field = "mt-1 min-h-11 rounded-md border border-ink-300 bg-white px-3 text-sm";
  return (
    <>
      <p className="max-w-prose text-ink-600">
        Change what happens for one team or role, for example HR may handle salary documents and
        Sales may not. The role rule wins over the team rule, and both win over the company policy.
      </p>
      <form onSubmit={add} className="mt-4 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="g-kind" className="block text-sm font-medium text-ink-700">
            Applies to
          </label>
          <select
            id="g-kind"
            className={field}
            value={draft.kind}
            onChange={(e) => setDraft({ ...draft, kind: e.target.value as GroupPolicy["kind"] })}
          >
            <option value="team">A team</option>
            <option value="role">A role</option>
          </select>
        </div>
        <div>
          <label htmlFor="g-group" className="block text-sm font-medium text-ink-700">
            Name
          </label>
          <input
            id="g-group"
            className={field}
            value={draft.group}
            onChange={(e) => setDraft({ ...draft, group: e.target.value })}
          />
        </div>
        <div>
          <label htmlFor="g-scope" className="block text-sm font-medium text-ink-700">
            Kind of rule
          </label>
          <select
            id="g-scope"
            className={field}
            value={draft.scope}
            onChange={(e) => {
              const scope = e.target.value as GroupPolicy["scope"];
              setDraft({
                ...draft,
                scope,
                key: scope === "category" ? CATEGORIES[0] : SENSITIVITIES[0],
              });
            }}
          >
            <option value="category">Sensitive data</option>
            <option value="sensitivity">Documents</option>
          </select>
        </div>
        <div>
          <label htmlFor="g-key" className="block text-sm font-medium text-ink-700">
            What
          </label>
          <select
            id="g-key"
            className={field}
            value={draft.key}
            onChange={(e) => setDraft({ ...draft, key: e.target.value })}
          >
            {keys.map((k) => (
              <option key={k} value={k}>
                {k.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="g-action" className="block text-sm font-medium text-ink-700">
            Then
          </label>
          <select
            id="g-action"
            className={field}
            value={draft.action}
            onChange={(e) => setDraft({ ...draft, action: e.target.value as Decision })}
          >
            {ACTIONS.map((a) => (
              <option key={a.id} value={a.id}>
                {a.label}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          className="min-h-11 rounded-md bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Add exception
        </button>
      </form>
      {error ? (
        <p role="alert" className="mt-3 text-sm font-semibold text-block-fg">
          {error}
        </p>
      ) : null}
      <section aria-label="Exceptions" className="mt-6">
        {list.length === 0 ? (
          <EmptyPanel title="No exceptions">
            <p>Everyone follows the company policy.</p>
          </EmptyPanel>
        ) : (
          <ul className="space-y-2">
            {list.map((o) => (
              <li
                key={`${o.kind}-${o.group}-${o.scope}-${o.key}`}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-ink-200 bg-white p-3"
              >
                <span className="text-sm text-ink-900">
                  {o.kind} <strong>{o.group}</strong>: {o.key.replace("_", " ")}
                </span>
                <span className="flex items-center gap-3">
                  <OutcomeChip outcome={o.action} />
                  <button
                    type="button"
                    aria-label={`Remove ${o.kind} ${o.group} ${o.key}`}
                    onClick={() => void run(() => deleteGroupPolicy(o))}
                    className="min-h-11 rounded-md px-3 text-sm font-medium text-ink-700 hover:bg-ink-100"
                  >
                    Remove
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
