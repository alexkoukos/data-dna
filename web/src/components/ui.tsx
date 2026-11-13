import type { ReactNode } from "react";
import { AlertIcon, BanIcon, CheckIcon } from "./icons";

/** Presentational building blocks shared by the security screens. */

export function DemoBadge() {
  return (
    <span className="inline-flex min-h-8 shrink-0 items-center whitespace-nowrap rounded-full border border-ink-300 bg-white px-3 text-xs font-semibold text-ink-700">
      Demo data
    </span>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-ink-200 ${className}`} />;
}

export function ErrorPanel({ what, onRetry }: { what: string; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="rounded-2xl border border-block-fg/30 bg-block-bg p-4 text-block-fg"
    >
      <p className="font-semibold">We could not load {what}.</p>
      <p className="mt-1 text-sm">The server did not answer. Try again in a moment.</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 min-h-11 rounded-lg bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700"
      >
        Try again
      </button>
    </div>
  );
}

export function EmptyPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-ink-300 bg-white p-6">
      <h2 className="text-lg font-semibold text-ink-900">{title}</h2>
      <div className="mt-1 max-w-prose text-ink-600">{children}</div>
    </div>
  );
}

const APPROVAL = {
  approved: { label: "Approved", style: "bg-allow-bg text-allow-fg", icon: <CheckIcon /> },
  tolerated: { label: "Tolerated", style: "bg-warn-bg text-warn-fg", icon: <AlertIcon /> },
  unapproved: { label: "Unapproved", style: "bg-block-bg text-block-fg", icon: <BanIcon /> },
} as const;

export function ApprovalBadge({ approval }: { approval: keyof typeof APPROVAL }) {
  const a = APPROVAL[approval];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${a.style}`}
    >
      {a.icon}
      {a.label}
    </span>
  );
}

export function RiskLabel({ risk }: { risk: "low" | "medium" | "high" }) {
  return (
    <span className={risk === "high" ? "font-semibold text-block-fg" : "text-ink-700"}>
      {risk === "high" ? "High risk" : risk === "medium" ? "Medium risk" : "Low risk"}
    </span>
  );
}

/** Tiny line chart of seven daily values. The numbers are in the label, so it is not color or shape alone. */
export function Sparkline({ values }: { values: number[] }) {
  const max = Math.max(...values, 1);
  const w = 84;
  const h = 24;
  const pts = values
    .map((v, i) => `${(i / Math.max(values.length - 1, 1)) * w},${h - (v / max) * (h - 2) - 1}`)
    .join(" ");
  return (
    <svg
      role="img"
      aria-label={`Requests per day, last 7 days: ${values.join(", ")}`}
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      className="text-brand-600"
    >
      <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}
