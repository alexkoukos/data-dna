import type { PolicyPreview } from "../lib/securityApi";

const WORD: Record<string, string> = {
  allow: "allowed",
  mask: "masked",
  warn: "warned",
  local: "answered locally",
  block: "blocked",
};

/** Presentational: what a policy change would have done to the last days of incidents (X12). */
export function PreviewResult({ preview }: { preview: PolicyPreview }) {
  if (preview.incidents_checked === 0) {
    return (
      <p className="mt-2 text-sm text-ink-700">
        There are no incidents in the last {preview.days} days to try this on.
      </p>
    );
  }
  if (preview.changed === 0) {
    return (
      <p className="mt-2 text-sm text-ink-700">
        On the last {preview.days} days ({preview.incidents_checked} incidents) this change would
        have made no difference.
      </p>
    );
  }
  return (
    <div className="mt-2 text-sm text-ink-700">
      <p className="font-semibold text-ink-900">
        On the last {preview.days} days this would have changed {preview.changed} of{" "}
        {preview.incidents_checked} incidents: {preview.stricter} stricter, {preview.looser} looser.
      </p>
      <ul className="mt-1 list-disc pl-5">
        {preview.moves.map((m) => (
          <li key={`${m.from}-${m.to}`}>
            {m.count} {m.count === 1 ? "message" : "messages"} {WORD[m.from]} would be {WORD[m.to]}
          </li>
        ))}
      </ul>
    </div>
  );
}
