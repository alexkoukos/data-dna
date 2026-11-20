import { AlertCircle, FileText, LoaderCircle, X } from "lucide-react";
import type { Attachment } from "../../lib/attachments";

interface Props {
  items: Attachment[];
  maxChars: number;
  onRemove: (id: string) => void;
}

/**
 * Presentational: the files attached to the next message, each with its state in words and an
 * icon (reading, ready, shortened, not added) and a remove button.
 */
export function AttachmentChips({ items, maxChars, onRemove }: Props) {
  if (!items.length) return null;
  const errors = items.filter((a) => a.status === "error");
  const cut = items.filter((a) => a.status === "ready" && a.truncated);
  return (
    <div className="px-3 pt-3">
      <ul className="flex flex-wrap gap-2" aria-label="Attached files" aria-live="polite">
        {items.map((a) => (
          <li
            key={a.id}
            className={`inline-flex min-h-11 max-w-full items-center gap-1.5 rounded-full border pl-3 text-xs ${
              a.status === "error"
                ? "border-transparent bg-block-bg text-block-fg"
                : "border-ink-200 bg-ink-50 text-ink-700"
            }`}
          >
            {a.status === "reading" ? (
              <LoaderCircle className="size-3.5 shrink-0 animate-spin" aria-hidden="true" />
            ) : a.status === "error" ? (
              <AlertCircle className="size-3.5 shrink-0" aria-hidden="true" />
            ) : (
              <FileText className="size-3.5 shrink-0" aria-hidden="true" />
            )}
            <span className="min-w-0 truncate font-medium">{a.name}</span>
            <span className="shrink-0">
              {a.status === "reading"
                ? "· Checking…"
                : a.status === "error"
                  ? "· Not added"
                  : a.truncated
                    ? "· Shortened"
                    : "· Ready"}
            </span>
            <button
              type="button"
              aria-label={`Remove ${a.name}`}
              className="grid size-11 shrink-0 place-items-center rounded-full hover:bg-ink-200 focus-visible:outline-2 focus-visible:outline-offset-[-4px] focus-visible:outline-ring"
              onClick={() => onRemove(a.id)}
            >
              <X className="size-3.5" aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
      {cut.length ? (
        <p className="mt-2 px-1 text-xs text-ink-600">
          {cut.map((a) => a.name).join(", ")} {cut.length === 1 ? "is" : "are"} long: only the first{" "}
          {maxChars.toLocaleString("en")} characters of each will be checked and sent.
        </p>
      ) : null}
      {errors.length ? (
        <ul role="alert" className="mt-2 space-y-1 px-1 text-sm text-block-fg">
          {errors.map((a) => (
            <li key={a.id}>{a.status === "error" ? a.message : null}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
