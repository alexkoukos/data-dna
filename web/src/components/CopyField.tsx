import { useState } from "react";
import { CheckIcon } from "./icons";
import { TextureButton } from "@/components/ui/texture-button";
import { Eye, EyeOff } from "lucide-react";

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
          className="min-h-11 min-w-0 flex-1 rounded-md border border-ink-300 bg-ink-50 px-3 font-mono text-sm text-ink-900"
        />
        {secret && (
          <TextureButton
            variant="secondary"
            type="button"
            aria-label={`${shown ? "Hide" : "Show"} ${label.toLowerCase()}`}
            onClick={() => setShown((s) => !s)}
          >
            {shown ? (
              <EyeOff className="size-4" aria-hidden="true" />
            ) : (
              <Eye className="size-4" aria-hidden="true" />
            )}
            {shown ? "Hide" : "Show"}
          </TextureButton>
        )}
        <TextureButton
          variant="secondary"
          type="button"
          aria-label={`Copy ${label.toLowerCase()}`}
          onClick={copy}
        >
          {copied ? (
            <span className="inline-flex items-center gap-1.5">
              <CheckIcon /> Copied
            </span>
          ) : (
            "Copy"
          )}
        </TextureButton>
      </div>
      <p role="status" className="sr-only">
        {copied ? `${label} copied` : ""}
      </p>
    </div>
  );
}
