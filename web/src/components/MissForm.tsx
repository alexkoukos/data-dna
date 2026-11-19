import { useState } from "react";
import { KIND_IDS, kindLabel, submitMiss } from "../lib/breakItApi";

const EXPECTED = [
  { id: "mask", label: "Mask it" },
  { id: "warn", label: "Warn" },
  { id: "block", label: "Block it" },
];

/** "It got through": the person says what should have happened and sends the text as a test case. */
export function MissForm({
  text,
  kind: initialKind,
  nickname,
  onSent,
}: {
  text: string;
  kind: string;
  nickname: string;
  onSent: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [expected, setExpected] = useState("warn");
  const [kind, setKind] = useState(initialKind);
  const [state, setState] = useState<"idle" | "busy" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  async function send() {
    setState("busy");
    setError(null);
    try {
      await submitMiss({ text, expected_decision: expected, kind, nickname });
      setState("sent");
      onSent();
    } catch (e) {
      setState("idle");
      setError(e instanceof Error ? e.message : "We could not send that.");
    }
  }

  if (state === "sent") {
    return (
      <p role="status" className="mt-4 rounded-2xl bg-allow-bg p-4 text-allow-fg">
        Thank you. The security team will review it before it joins the test set.
      </p>
    );
  }
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-4 min-h-11 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-[#1a1000] hover:bg-brand-700"
      >
        It got through
      </button>
    );
  }
  return (
    <form
      aria-label="Send as a test case"
      className="mt-4 rounded-2xl border border-ink-200 bg-surface p-4"
      onSubmit={(e) => {
        e.preventDefault();
        void send();
      }}
    >
      <fieldset>
        <legend className="text-sm font-semibold text-ink-900">What should have happened?</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {EXPECTED.map((x) => (
            <label
              key={x.id}
              className="flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-ink-300 px-4 text-sm"
            >
              <input
                type="radio"
                name="expected"
                value={x.id}
                checked={expected === x.id}
                onChange={() => setExpected(x.id)}
              />
              {x.label}
            </label>
          ))}
        </div>
      </fieldset>
      <label htmlFor="miss-kind" className="mt-4 block text-sm font-semibold text-ink-900">
        Kind of trick
      </label>
      <select
        id="miss-kind"
        value={kind}
        onChange={(e) => setKind(e.target.value)}
        className="mt-1 min-h-11 w-full rounded-lg border border-ink-300 bg-surface px-3 text-ink-900 sm:w-auto"
      >
        {KIND_IDS.map((k) => (
          <option key={k} value={k}>
            {kindLabel(k)}
          </option>
        ))}
      </select>
      <p className="mt-4 max-w-prose text-sm text-ink-600">
        Pressing the button below saves the exact text you typed, so the team can review it and add
        it to the test set. Nothing else you typed is saved. If the team rejects it, it is deleted.
        Do not send real personal data.
      </p>
      {error ? (
        <p role="alert" className="mt-3 text-sm font-medium text-block-fg">
          {error}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={state === "busy"}
          aria-busy={state === "busy"}
          className="min-h-11 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-[#1a1000] hover:bg-brand-700 disabled:opacity-60"
        >
          {state === "busy" ? "Sending…" : "Send this text as a test case"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="min-h-11 rounded-lg px-3 text-sm font-medium text-ink-600 hover:bg-ink-100"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
