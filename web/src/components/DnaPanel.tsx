import { useState } from "react";
import {
  approveMarks,
  fetchDnaState,
  issueCopies,
  proposeMarks,
  type IssuedCopy,
  type ProposedMark,
} from "../lib/securityApi";
import { ErrorPanel, Skeleton } from "./ui";
import { useFetch } from "../lib/useFetch";

const primary =
  "min-h-11 rounded-lg bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60";

/** Per-copy marks for one document: propose, approve, issue copies, open a copy. */
export function DnaPanel({ documentId }: { documentId: number }) {
  const [state, reload] = useFetch(() => fetchDnaState(documentId));
  const [proposal, setProposal] = useState<ProposedMark[] | null>(null);
  const [recipients, setRecipients] = useState("");
  const [issued, setIssued] = useState<IssuedCopy[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not work.");
    } finally {
      setBusy(false);
    }
  }

  if (state.status === "loading") return <Skeleton className="mt-3 h-12" />;
  if (state.status === "error") return <ErrorPanel what="the marks" onRetry={reload} />;

  const names = recipients
    .split(/[,\n]/)
    .map((x) => x.trim())
    .filter(Boolean);
  return (
    <div className="mt-3 border-t border-ink-100 pt-3">
      <h4 className="text-sm font-semibold text-ink-900">Per-copy marks</h4>
      {!state.data.enabled ? (
        <>
          <p className="mt-1 max-w-prose text-sm text-ink-700">
            Marks are small decoy details that differ for each person who receives the document. If
            it leaks, the marks name the copy. Nothing in the original text is changed.
          </p>
          {proposal ? (
            <>
              <ul className="mt-2 space-y-1 text-sm text-ink-900">
                {proposal.map((m) => (
                  <li key={m.position}>
                    After sentence {m.position + 1}:{" "}
                    <span className="font-mono">{m.variants.join(", ")}</span>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                disabled={busy}
                className={`${primary} mt-3`}
                onClick={() =>
                  run(async () => {
                    await approveMarks(documentId, proposal);
                    setProposal(null);
                    reload();
                  })
                }
              >
                Approve these {proposal.length} marks
              </button>
            </>
          ) : (
            <button
              type="button"
              disabled={busy}
              className={`${primary} mt-2`}
              onClick={() => run(async () => setProposal((await proposeMarks(documentId)).marks))}
            >
              Suggest marks
            </button>
          )}
        </>
      ) : (
        <>
          <p className="mt-1 text-sm text-ink-700">
            {state.data.marks} marks approved. {state.data.copies.length} copies issued
            {state.data.copies.length ? `: ${state.data.copies.join(", ")}` : ""}.
          </p>
          <label className="mt-3 block text-sm font-medium text-ink-700">
            Who gets a copy? Pseudonyms, separated by commas
            <textarea
              value={recipients}
              onChange={(e) => setRecipients(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-lg border border-ink-300 px-3 py-2 text-sm text-ink-900"
            />
          </label>
          <button
            type="button"
            disabled={busy || names.length === 0}
            className={`${primary} mt-2`}
            onClick={() =>
              run(async () => {
                setIssued(await issueCopies(documentId, names));
                setRecipients("");
                reload();
              })
            }
          >
            Issue copies
          </button>
          {issued.length > 0 ? (
            <ul className="mt-3 space-y-1 text-sm text-ink-900">
              {issued.map((c) => (
                <li key={c.copy_code}>
                  {c.recipient}: copy <span className="font-mono font-semibold">{c.copy_code}</span>{" "}
                  <a
                    className="inline-flex min-h-11 items-center font-semibold text-brand-700 underline"
                    href={`/api/v1/documents/${documentId}/copies/${c.copy_code}`}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Open copy ${c.copy_code}`}
                  >
                    Open it
                  </a>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}
      {error ? (
        <p role="alert" className="mt-2 text-sm font-semibold text-block-fg">
          {error}
        </p>
      ) : null}
    </div>
  );
}
