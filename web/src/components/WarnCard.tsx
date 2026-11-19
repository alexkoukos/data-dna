import { useState } from "react";
import { explainReason } from "../lib/explain";
import { AlertIcon } from "./icons";
import { TextureButton } from "@/components/ui/texture-button";
import { Sentinel } from "./Sentinel";
import { Pencil, SendHorizontal, ShieldCheck, X } from "lucide-react";

interface Props {
  reasons: string[];
  /** A masked version of the message the person can send instead (X19). */
  suggestion?: string;
  onUseSuggestion?: () => void;
  onEdit: () => void;
  onSendAnyway: (reason: string) => void;
  onCancel: () => void;
  /** X31: send the message to Company AI instead. The gate masks it first. */
  onReroute?: () => void;
  busy?: boolean;
}

/** Presentational: asks before a risky message goes out. Editing is the safe, primary choice. */
export function WarnCard({
  reasons,
  suggestion,
  onUseSuggestion,
  onEdit,
  onSendAnyway,
  onCancel,
  onReroute,
  busy,
}: Props) {
  const [reason, setReason] = useState("");
  return (
    <section
      aria-labelledby="warn-title"
      className="rounded-lg border border-warn-fg/30 bg-warn-bg p-4 text-warn-fg"
    >
      <div className="flex flex-wrap items-center gap-4">
        <Sentinel size={80} />
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
      {suggestion ? (
        <div className="mt-4">
          <p className="text-sm font-medium">A safer version of your message:</p>
          <p
            aria-label="Safer version"
            className="mt-1 whitespace-pre-wrap rounded-md border border-ink-200 bg-surface p-3 text-sm text-ink-900"
          >
            {suggestion}
          </p>
        </div>
      ) : null}
      <label htmlFor="warn-reason" className="mt-4 block text-sm font-medium">
        Need to send it as it is? Say why (this is saved with the message).
      </label>
      <input
        id="warn-reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="mt-1 min-h-11 w-full rounded-md border border-ink-300 bg-surface px-3 text-base text-ink-900"
      />
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {suggestion && onUseSuggestion ? (
          <TextureButton type="button" onClick={onUseSuggestion} disabled={busy} variant="primary">
            <ShieldCheck className="size-4" aria-hidden="true" />
            Send the safer version
          </TextureButton>
        ) : null}
        <TextureButton
          type="button"
          onClick={onEdit}
          disabled={busy}
          variant={suggestion && onUseSuggestion ? "secondary" : "primary"}
        >
          <Pencil className="size-4" aria-hidden="true" />
          Edit message
        </TextureButton>
        <TextureButton
          variant="secondary"
          type="button"
          onClick={() => onSendAnyway(reason.trim())}
          disabled={busy || reason.trim().length === 0}
        >
          <SendHorizontal className="size-4" aria-hidden="true" />
          Send anyway
        </TextureButton>
        {onReroute ? (
          <TextureButton type="button" onClick={onReroute} disabled={busy} variant="secondary">
            <ShieldCheck className="size-4" aria-hidden="true" />
            Send it to Company AI instead
          </TextureButton>
        ) : null}
        <TextureButton type="button" onClick={onCancel} disabled={busy} variant="minimal">
          <X className="size-4" aria-hidden="true" />
          Cancel
        </TextureButton>
      </div>
    </section>
  );
}
