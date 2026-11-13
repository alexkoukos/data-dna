import { EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import { textFor } from "../../lib/policyText";
import { fetchDocuments } from "../../lib/securityApi";
import { useFetch } from "../../lib/useFetch";

/** Container: the register of protected documents. Marks and copies arrive with the DNA task. */
export default function DocumentsPage() {
  const [state, reload] = useFetch(fetchDocuments);

  if (state.status === "loading") {
    return (
      <div role="status" aria-label="Loading documents" className="space-y-3">
        {[0, 1, 2].map((n) => (
          <Skeleton key={n} className="h-24" />
        ))}
      </div>
    );
  }
  if (state.status === "error") return <ErrorPanel what="the documents" onRetry={reload} />;
  if (state.data.length === 0) {
    return (
      <EmptyPanel title="No protected documents yet">
        <p>
          Once a confidential document is registered, the gateway recognises it even when it is
          rewritten, and it shows up here.
        </p>
      </EmptyPanel>
    );
  }

  return (
    <>
      <p className="max-w-prose text-ink-600">
        Documents the gateway protects. The sensitivity decides what happens when someone pastes
        them into an AI tool; change that on the Policies tab.
      </p>
      <ul className="mt-4 space-y-3">
        {state.data.map((d) => (
          <li key={d.id} className="rounded-2xl border border-ink-200 bg-white p-4">
            <h3 className="text-base font-semibold text-ink-900">{d.title}</h3>
            <dl className="mt-2 flex flex-wrap gap-x-8 gap-y-2 text-sm text-ink-600">
              <div>
                <dt>Sensitivity</dt>
                <dd className="font-medium text-ink-900">
                  {textFor("sensitivity", d.sensitivity).label.replace(" documents", "")}
                </dd>
              </div>
              <div>
                <dt>Incidents</dt>
                <dd className="font-medium tabular-nums text-ink-900">{d.incidents}</dd>
              </div>
              <div>
                <dt>Per-copy marks</dt>
                <dd className="font-medium text-ink-900">
                  {d.dna_enabled ? "On" : "Not set up yet"}
                </dd>
              </div>
              {d.created_at ? (
                <div>
                  <dt>Added</dt>
                  <dd className="font-medium text-ink-900">{d.created_at.slice(0, 10)}</dd>
                </div>
              ) : null}
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}
