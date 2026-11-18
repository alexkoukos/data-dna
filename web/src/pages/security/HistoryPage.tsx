import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { IncidentRow } from "../../components/IncidentRow";
import { EmptyPanel, ErrorPanel, Skeleton } from "../../components/ui";
import {
  fetchDocumentHistory,
  fetchDocuments,
  fetchUserHistory,
  type History,
} from "../../lib/securityApi";
import { useFetch } from "../../lib/useFetch";
import { TextureButton } from "@/components/ui/texture-button";
import { Search } from "lucide-react";

function Result({ history, what }: { history: History; what: string }) {
  if (history.total === 0) {
    return (
      <EmptyPanel title="Nothing recorded">
        No incidents were found for {what}. That is good news, or they have not used the gate yet.
      </EmptyPanel>
    );
  }
  return (
    <section aria-label={`History of ${what}`}>
      <p className="text-sm text-ink-700">
        {history.total} incidents. Only masked previews are shown.{" "}
        {Object.entries(history.by_decision)
          .map(([d, n]) => `${n} ${d}`)
          .join(", ")}
        .
      </p>
      <ul className="mt-3 space-y-3">
        {history.items.map((i) => (
          <IncidentRow key={i.id} incident={i} />
        ))}
      </ul>
    </section>
  );
}

function UserHistory({ user }: { user: string }) {
  const [state, reload] = useFetch(() => fetchUserHistory(user));
  if (state.status === "loading") return <Skeleton className="h-32" aria-label="Loading history" />;
  if (state.status === "error") return <ErrorPanel what="this history" onRetry={reload} />;
  return <Result history={state.data} what={user} />;
}

function DocumentHistory({ id }: { id: number }) {
  const [state, reload] = useFetch(() => fetchDocumentHistory(id));
  if (state.status === "loading") return <Skeleton className="h-32" aria-label="Loading history" />;
  if (state.status === "error") return <ErrorPanel what="this history" onRetry={reload} />;
  return <Result history={state.data} what={state.data.subject ?? "this document"} />;
}

/** X24: everything one person triggered, or every incident that matched one document. */
export default function HistoryPage() {
  const [params, setParams] = useSearchParams();
  const user = params.get("user") ?? "";
  const doc = Number(params.get("document")) || null;
  const [draft, setDraft] = useState(user);
  const [docs] = useFetch(fetchDocuments);

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold text-ink-900">History</h2>
        <p className="max-w-prose text-ink-700">
          Look back at one person or one document. People appear as pseudonyms; a real name needs
          the two-person reveal.
        </p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (draft.trim()) setParams({ user: draft.trim() });
          }}
        >
          <label htmlFor="h-user" className="block text-sm font-medium text-ink-700">
            Person (pseudonym)
          </label>
          <div className="mt-1 flex gap-2">
            <input
              id="h-user"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="min-h-11 w-full rounded-md border border-ink-300 bg-white px-3 text-sm text-ink-900"
            />
            <TextureButton type="submit" variant="primary">
              <Search className="size-4" aria-hidden="true" />
              Show
            </TextureButton>
          </div>
        </form>
        <div>
          <label htmlFor="h-doc" className="block text-sm font-medium text-ink-700">
            Document
          </label>
          <select
            id="h-doc"
            value={doc ?? ""}
            onChange={(e) => e.target.value && setParams({ document: e.target.value })}
            className="mt-1 min-h-11 w-full rounded-md border border-ink-300 bg-white px-3 text-sm text-ink-900"
          >
            <option value="">Choose a document</option>
            {docs.status === "ready"
              ? docs.data.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title}
                  </option>
                ))
              : null}
          </select>
        </div>
      </div>
      {user ? <UserHistory key={user} user={user} /> : null}
      {!user && doc ? <DocumentHistory key={doc} id={doc} /> : null}
      {!user && !doc ? (
        <EmptyPanel title="Pick a person or a document">
          Type a pseudonym such as the ones in the incident list, or choose a document, to replay
          what happened.
        </EmptyPanel>
      ) : null}
    </div>
  );
}
