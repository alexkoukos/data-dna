import type { FormEvent, KeyboardEvent } from "react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled?: boolean;
}

/** Presentational: message box. Enter sends, Shift+Enter adds a line. */
export function Composer({ value, onChange, onSend, disabled }: Props) {
  const canSend = !disabled && value.trim().length > 0;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (canSend) onSend();
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) onSend();
    }
  };
  return (
    <form onSubmit={submit} className="flex items-end gap-2">
      <textarea
        aria-label="Message"
        rows={2}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKey}
        placeholder="Ask anything. Shift+Enter adds a new line."
        className="min-h-11 flex-1 resize-none rounded-md border border-ink-300 bg-white px-3 py-2 text-base"
      />
      <button
        type="submit"
        disabled={!canSend}
        className="min-h-11 rounded-md bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-ink-200 disabled:text-ink-700"
      >
        Send
      </button>
    </form>
  );
}
