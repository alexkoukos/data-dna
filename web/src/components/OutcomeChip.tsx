import type { ReactNode } from "react";
import { AlertIcon, BanIcon, CheckIcon, EyeOffIcon, HomeIcon } from "./icons";

export type Outcome = "allow" | "mask" | "warn" | "local" | "block";

const LABELS: Record<Outcome, string> = {
  allow: "Allowed",
  mask: "Masked",
  warn: "Warned",
  local: "Answered locally",
  block: "Blocked",
};

const STYLES: Record<Outcome, string> = {
  allow: "bg-allow-bg text-allow-fg",
  mask: "bg-mask-bg text-mask-fg",
  warn: "bg-warn-bg text-warn-fg",
  local: "bg-local-bg text-local-fg",
  block: "bg-block-bg text-block-fg",
};

const DOTS: Record<Outcome, string> = {
  allow: "bg-allow-solid",
  mask: "bg-mask-solid",
  warn: "bg-warn-solid",
  local: "bg-local-solid",
  block: "bg-block-solid",
};

const ICONS: Record<Outcome, ReactNode> = {
  allow: <CheckIcon />,
  mask: <EyeOffIcon />,
  warn: <AlertIcon />,
  local: <HomeIcon />,
  block: <BanIcon />,
};

/** Presentational: shows an outcome with an icon and text, never color alone. */
export function OutcomeChip({ outcome, detail }: { outcome: Outcome; detail?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm px-2.5 py-1 text-xs font-semibold ${STYLES[outcome]}`}
    >
      <span aria-hidden="true" className={`size-2 rounded-full ${DOTS[outcome]}`} />
      {ICONS[outcome]}
      {LABELS[outcome]}
      {detail ? <span className="font-medium">· {detail}</span> : null}
    </span>
  );
}
