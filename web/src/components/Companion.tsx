import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { DECISION_EVENT, ERROR_EVENT, SAYS } from "../lib/companion";
import { fetchIncidents } from "../lib/securityApi";
import { OutcomeChip, type Outcome } from "./OutcomeChip";
import { Thyro } from "./Thyro";

type Corner = "right" | "left";
const KEY = "pyli.companion";
/** How long Thyro stays after an event. */
export const VISIBLE_MS = 6000;
const SIZE = 96;

function loadCorner(): Corner {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "{}") as { corner?: Corner };
    return v.corner === "left" ? "left" : "right";
  } catch {
    return "right";
  }
}

type Shown =
  { kind: "decision"; outcome: Outcome; detail?: string } | { kind: "error"; message: string };

const btn =
  "grid size-11 shrink-0 place-items-center rounded-md border border-ink-200 bg-white text-ink-700 hover:bg-ink-100";

function Icon({ d }: { d: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={d} />
    </svg>
  );
}

/** Container: Thyro is hidden until the gate decides something or an error happens, stays for six
 * seconds, then leaves. He sits in a bottom corner (above the message box on the chat screen). */
export function Companion() {
  const [corner, setCorner] = useState<Corner>(loadCorner);
  const [shown, setShown] = useState<Shown | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const lastSeen = useRef<number | null>(null);
  const onChat = useLocation().pathname.startsWith("/chat");

  const moveCorner = () =>
    setCorner((c) => {
      const next: Corner = c === "right" ? "left" : "right";
      try {
        localStorage.setItem(KEY, JSON.stringify({ corner: next }));
      } catch {
        // The corner is a convenience; the companion still works without it.
      }
      return next;
    });

  const show = useCallback((s: Shown) => {
    setShown(s);
    setCollapsed(false);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setShown(null), VISIBLE_MS);
  }, []);

  useEffect(() => {
    const onDecision = (e: Event) => {
      const { outcome, detail } = (e as CustomEvent<{ outcome: Outcome; detail?: string }>).detail;
      show({ kind: "decision", outcome, detail });
    };
    const onError = (e: Event) => {
      show({ kind: "error", message: (e as CustomEvent<{ message: string }>).detail.message });
    };
    window.addEventListener(DECISION_EVENT, onDecision);
    window.addEventListener(ERROR_EVENT, onError);
    return () => {
      window.removeEventListener(DECISION_EVENT, onDecision);
      window.removeEventListener(ERROR_EVENT, onError);
      window.clearTimeout(timer.current);
    };
  }, [show]);

  // Decisions made elsewhere (another tool going through the gate) show up within seconds.
  useEffect(() => {
    let stop = false;
    const poll = async () => {
      try {
        const page = await fetchIncidents("all", 0, 1);
        const latest = page.items[0];
        if (!latest || stop) return;
        if (lastSeen.current !== null && latest.id !== lastSeen.current) {
          show({ kind: "decision", outcome: latest.decision });
        }
        lastSeen.current = latest.id;
      } catch {
        // The companion is decoration: a failed poll is not worth a message.
      }
    };
    void poll();
    const id = window.setInterval(poll, 5000);
    return () => {
      stop = true;
      window.clearInterval(id);
    };
  }, [show]);

  if (shown === null) return null;

  const side = corner === "right" ? "right-4 flex-row-reverse" : "left-4";
  // Above the message box on chat, near the bottom edge elsewhere. Never over the input.
  const lift = onChat ? "bottom-36 max-md:bottom-44" : "bottom-4";
  const pose = shown.kind === "error" ? "error" : shown.outcome;
  const words = shown.kind === "error" ? shown.message : SAYS[shown.outcome];

  return (
    <aside
      aria-label="Thyro, your companion"
      className={`pointer-events-none fixed z-40 flex items-end gap-2 ${lift} ${side}`}
    >
      {collapsed ? (
        <button
          type="button"
          aria-label="Show Thyro"
          onClick={() => setCollapsed(false)}
          className="pointer-events-auto grid size-11 place-items-center rounded-full border border-ink-200 bg-white p-1"
        >
          <Thyro pose="avatar" size={32} />
        </button>
      ) : (
        <div className="pointer-events-auto flex max-w-[calc(100vw-2rem)] items-end gap-2 rounded-lg border border-ink-200 bg-white p-2 shadow-md">
          <Thyro pose={pose} size={SIZE} />
          <div
            aria-live="polite"
            className="flex min-w-0 max-w-[14rem] flex-col items-start gap-1.5 self-center text-sm text-ink-900"
          >
            {shown.kind === "decision" ? (
              <OutcomeChip outcome={shown.outcome} detail={shown.detail} />
            ) : null}
            <p>{words}</p>
          </div>
          <div className="flex flex-col gap-1 self-start">
            <button
              type="button"
              aria-label="Hide Thyro"
              title="Hide"
              onClick={() => setCollapsed(true)}
              className={btn}
            >
              <Icon d="M6 6l12 12M18 6L6 18" />
            </button>
            <button
              type="button"
              aria-label={
                corner === "right"
                  ? "Move Thyro to the bottom left"
                  : "Move Thyro to the bottom right"
              }
              title="Move to the other corner"
              onClick={moveCorner}
              className={`${btn} max-md:hidden`}
            >
              <Icon d={corner === "right" ? "M19 12H5M12 5l-7 7 7 7" : "M5 12h14M12 5l7 7-7 7"} />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
