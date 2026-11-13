import type { Outcome } from "../components/OutcomeChip";
import { line } from "../mascot/copy";

export const DECISION_EVENT = "pyli:decision";
export const ERROR_EVENT = "pyli:error";

/** Tells the companion that the gate just made a decision. Any screen can call this. */
export function announce(outcome: Outcome, detail?: string): void {
  window.dispatchEvent(new CustomEvent(DECISION_EVENT, { detail: { outcome, detail } }));
}

/** Tells the companion that something went wrong and what the person can do next. */
export function announceError(message: string): void {
  window.dispatchEvent(new CustomEvent(ERROR_EVENT, { detail: { message } }));
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
