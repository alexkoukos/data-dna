import type { Outcome } from "../components/OutcomeChip";
import { line } from "../mascot/copy";

export const DECISION_EVENT = "pyli:decision";

/** Tells the companion that the gate just made a decision. Any screen can call this. */
export function announce(outcome: Outcome, detail?: string): void {
  window.dispatchEvent(new CustomEvent(DECISION_EVENT, { detail: { outcome, detail } }));
}

export const SAYS = {
  get idle() {
    return line("idle");
  },
  get allow() {
    return line("allow");
  },
  get warn() {
    return line("warn");
  },
  get mask() {
    return line("mask");
  },
  get local() {
    return line("local");
  },
  get block() {
    return line("block");
  },
} as Record<Outcome | "idle", string>;
