import { useState } from "react";
import { explainReason } from "../lib/explain";
import { AlertIcon } from "./icons";
import { Thyro } from "./Thyro";

interface Props {
  reasons: string[];
  onEdit: () => void;
  onSendAnyway: (reason: string) => void;
  onCancel: () => void;
  busy?: boolean;
}

/** Presentational: asks before a risky message goes out. Editing is the safe, primary choice. */
export function WarnCard({ reasons, onEdit, onSendAnyway, onCancel, busy }: Props) {
  const [reason, setReason] = useState("");
  return (
    <section
      aria-labelledby="warn-title"
      className="rounded-lg border border-warn-fg/30 bg-warn-bg p-4 text-warn-fg"
    >
      <div className="flex flex-wrap items-center gap-4">
        <Thyro pose="warn" />
        <div className="min-w-0 flex-1">
          <h2 id="warn-title" className="flex items-center gap-2 text-base font-semibold">
            <AlertIcon />
            Check before this goes out
          </h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {reasons.map((r) => (
              <li key={r}>{explainReason(r)}</li>
            ))}
          </ul>
        </div>
      </div>
      <label htmlFor="warn-reason" className="mt-4 block text-sm font-medium">
        Need to send it as it is? Say why (this is saved with the message).
      </label>
      <input
        id="warn-reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="mt-1 min-h-11 w-full rounded-md border border-ink-300 bg-white px-3 text-base text-ink-900"
      />
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onEdit}
          disabled={busy}
          className="min-h-11 rounded-md bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
        >
          Edit message
        </button>
        <button
          type="button"
          onClick={() => onSendAnyway(reason.trim())}
          disabled={busy || reason.trim().length === 0}
          className="min-h-11 rounded-md border border-warn-fg/40 bg-white px-4 text-sm font-semibold text-warn-fg hover:bg-ink-50 disabled:opacity-60"
        >
          Send anyway
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          className="min-h-11 rounded-md px-3 text-sm font-medium underline"
        >
          Cancel
        </button>
      </div>
    </section>
  );
}
