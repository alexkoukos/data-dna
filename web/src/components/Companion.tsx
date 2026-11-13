import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { DECISION_EVENT, SAYS } from "../lib/companion";
import { fetchIncidents } from "../lib/securityApi";
import { openVideoPip, openWindowPip, pipSupport, type VideoPip } from "../lib/pip";
import { OutcomeChip, type Outcome } from "./OutcomeChip";
import { Thyro, type ThyroPose } from "./Thyro";

type Corner = "right" | "left";
const KEY = "pyli.companion";

function load(): { corner: Corner; hidden: boolean } {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "{}") as Partial<{
      corner: Corner;
      hidden: boolean;
    }>;
    return { corner: v.corner === "left" ? "left" : "right", hidden: v.hidden === true };
  } catch {
    return { corner: "right", hidden: false };
  }
}

/** Presentational: Thyro with what he just did, in words. Used in the page and in the floating window. */
export function CompanionBody({
  outcome,
  detail,
  size,
}: {
  outcome: Outcome | null;
  detail?: string;
  size: number;
}) {
  const pose: ThyroPose = outcome ?? "master";
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <div
        aria-live="polite"
        className="chip-pop max-w-[18rem] rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 shadow-md"
        key={`${outcome}-${detail}`}
      >
        {outcome ? (
          <div className="mb-1 flex justify-center">
            <OutcomeChip outcome={outcome} detail={detail} />
          </div>
        ) : null}
        {SAYS[outcome ?? "idle"]}
      </div>
      <Thyro pose={pose} size={size} />
    </div>
  );
}

const btn =
  "grid size-11 place-items-center rounded-md border border-ink-200 bg-white text-ink-700 shadow-sm hover:bg-ink-100";

function Icon({ d }: { d: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={d} />
    </svg>
  );
}

/** Container: Thyro lives in a bottom corner on every screen, reacts to every decision, and can float
 * on top of other windows (picture in picture). */
export function Companion() {
  const [{ corner, hidden }, setPrefs] = useState(load);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [detail, setDetail] = useState<string | undefined>();
  const [pipWin, setPipWin] = useState<Window | null>(null);
  const [videoPip, setVideoPip] = useState<VideoPip | null>(null);
  const [pipError, setPipError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const lastSeen = useRef<number | null>(null);
  const support = pipSupport();
  // On the chat screen he sits above the message box, so he never covers what people type.
  const onChat = useLocation().pathname.startsWith("/chat");

  const save = (next: Partial<{ corner: Corner; hidden: boolean }>) =>
    setPrefs((p) => {
      const n = { ...p, ...next };
      try {
        localStorage.setItem(KEY, JSON.stringify(n));
      } catch {
        // Preferences are a convenience; the companion still works without them.
      }
      return n;
    });

  const show = useCallback((o: Outcome, d?: string) => {
    setOutcome(o);
    setDetail(d);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setOutcome(null), 9000);
  }, []);

  useEffect(() => {
    const on = (e: Event) => {
      const { outcome: o, detail: d } = (e as CustomEvent<{ outcome: Outcome; detail?: string }>)
        .detail;
      show(o, d);
    };
    window.addEventListener(DECISION_EVENT, on);
    return () => {
      window.removeEventListener(DECISION_EVENT, on);
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
        if (lastSeen.current !== null && latest.id !== lastSeen.current) show(latest.decision);
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

  // Keep the video fallback in step with what Thyro is doing.
  useEffect(() => {
    videoPip?.update(
      `${window.location.origin}/mascot/thyro-${outcome ?? "master"}.svg`,
      SAYS[outcome ?? "idle"],
    );
  }, [videoPip, outcome]);

  async function popOut() {
    setPipError(null);
    try {
      if (support === "window") {
        const win = await openWindowPip();
        win.addEventListener("pagehide", () => setPipWin(null), { once: true });
        setPipWin(win);
      } else if (support === "video") {
        const v = await openVideoPip(
          `${window.location.origin}/mascot/thyro-${outcome ?? "master"}.svg`,
          SAYS[outcome ?? "idle"],
          () => setVideoPip(null),
        );
        setVideoPip(v);
      }
    } catch {
      setPipError("Your browser did not allow the floating window. Try again from a click.");
    }
  }
  function popBack() {
    pipWin?.close();
    videoPip?.close();
    setPipWin(null);
    setVideoPip(null);
  }

  const floating = pipWin !== null || videoPip !== null;
  const side = corner === "right" ? "right-4 items-end" : "left-4 items-start";

  if (hidden) {
    return (
      <button
        type="button"
        aria-label="Show Thyro"
        onClick={() => save({ hidden: false })}
        className={`fixed bottom-4 z-40 rounded-full border border-ink-200 bg-white p-1 shadow-lg hover:scale-105 ${corner === "right" ? "right-4" : "left-4"}`}
      >
        <Thyro pose="avatar" size={56} />
      </button>
    );
  }

  return (
    <aside
      aria-label="Thyro, your companion"
      className={`pointer-events-none fixed z-40 flex flex-col gap-2 ${onChat ? "bottom-36" : "bottom-4 max-md:bottom-24"} ${side}`}
    >
      {pipWin
        ? createPortal(
            <div className="p-4">
              <CompanionBody outcome={outcome} detail={detail} size={260} />
            </div>,
            pipWin.document.body,
          )
        : null}
      {floating ? (
        <div className="pointer-events-auto rounded-lg border border-ink-200 bg-white p-3 text-sm text-ink-700 shadow-md">
          <p>Thyro is floating on top of your other windows.</p>
          <button
            type="button"
            onClick={popBack}
            className={`${btn} mt-2 w-auto px-3 text-sm font-medium`}
          >
            Bring him back
          </button>
        </div>
      ) : (
        <div className="pointer-events-auto group relative">
          <CompanionBody outcome={outcome} detail={detail} size={208} />
          <div
            className={`absolute bottom-0 flex flex-col gap-2 opacity-80 transition-opacity group-hover:opacity-100 focus-within:opacity-100 ${corner === "right" ? "-left-14" : "-right-14"} max-md:hidden`}
          >
            {support ? (
              <button
                type="button"
                aria-label="Float Thyro on top of other windows"
                title="Picture in picture"
                onClick={popOut}
                className={btn}
              >
                <Icon d="M3 5h18v14H3zM12 12h7v5h-7z" />
              </button>
            ) : null}
            <button
              type="button"
              aria-label={
                corner === "right"
                  ? "Move Thyro to the bottom left"
                  : "Move Thyro to the bottom right"
              }
              title="Move to the other corner"
              onClick={() => save({ corner: corner === "right" ? "left" : "right" })}
              className={btn}
            >
              <Icon d={corner === "right" ? "M19 12H5M12 5l-7 7 7 7" : "M5 12h14M12 5l7 7-7 7"} />
            </button>
            <button
              type="button"
              aria-label="Hide Thyro"
              title="Hide"
              onClick={() => save({ hidden: true })}
              className={btn}
            >
              <Icon d="M6 6l12 12M18 6L6 18" />
            </button>
          </div>
          {pipError ? (
            <p
              role="alert"
              className="mt-2 max-w-[18rem] rounded-md bg-block-bg p-2 text-sm text-block-fg"
            >
              {pipError}
            </p>
          ) : null}
        </div>
      )}
    </aside>
  );
}
