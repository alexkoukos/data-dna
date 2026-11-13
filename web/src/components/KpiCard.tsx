import type { ReactNode } from "react";

/** Presentational: one number, its name, and a short note. The number leads, the label supports it. */
export function KpiCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-ink-200 bg-white p-4">
      <p className="text-sm font-medium text-ink-600">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums text-ink-900">{value}</p>
      {note ? <p className="mt-1 text-sm text-ink-600">{note}</p> : null}
    </div>
  );
}
