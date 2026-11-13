import { useState } from "react";
import { CheckIcon } from "./icons";

interface Props {
  label: string;
  value: string;
  /** Show dots until the user asks to see the value (used for the personal key). */
  secret?: boolean;
}

/** A read-only value with Copy (and Show or Hide for secrets). */
export function CopyField({ label, value, secret = false }: Props) {
  const [shown, setShown] = useState(!secret);
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard can be blocked. Showing the value lets the person select it by hand.
      setShown(true);
    }
  }

  const btn =
    "min-h-11 min-w-11 rounded-lg border border-ink-300 bg-white px-3 text-sm font-semibold text-ink-900 hover:bg-ink-100";
  return (
    <div>
      <label htmlFor={`f-${label}`} className="block text-sm font-semibold text-ink-900">
        {label}
      </label>
      <div className="mt-1 flex flex-wrap gap-2">
        <input
          id={`f-${label}`}
          readOnly
          value={shown ? value : "•".repeat(Math.min(value.length, 24))}
          className="min-h-11 min-w-0 flex-1 rounded-lg border border-ink-300 bg-ink-50 px-3 font-mono text-sm text-ink-900"
        />
        {secret && (
          <button
            type="button"
            aria-label={`${shown ? "Hide" : "Show"} ${label.toLowerCase()}`}
            onClick={() => setShown((s) => !s)}
            className={btn}
          >
            {shown ? "Hide" : "Show"}
          </button>
        )}
        <button
          type="button"
          aria-label={`Copy ${label.toLowerCase()}`}
          onClick={copy}
          className={btn}
        >
          {copied ? (
            <span className="inline-flex items-center gap-1.5">
              <CheckIcon /> Copied
            </span>
          ) : (
            "Copy"
          )}
        </button>
      </div>
      <p role="status" className="sr-only">
        {copied ? `${label} copied` : ""}
      </p>
    </div>
  );
}
