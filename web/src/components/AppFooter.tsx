import { Link } from "react-router-dom";
import type { GateHealth } from "../lib/healthApi";
import { APP_FOOTER_ID } from "../lib/useLiftAboveFooter";

const GITHUB = "https://github.com/alexkoukos/data-dna";

// Text and glyph carry the meaning; the color only repeats it.
const STATUS: Record<GateHealth, { glyph: string; text: string; className: string }> = {
  checking: { glyph: "…", text: "Checking the gate", className: "text-ink-600" },
  online: { glyph: "●", text: "Gate online", className: "text-allow-fg" },
  degraded: {
    glyph: "▲",
    text: "Gate online, database unreachable. Run make up.",
    className: "text-warn-fg",
  },
  offline: {
    glyph: "■",
    text: "Gate offline. Start it with make up.",
    className: "text-block-fg",
  },
};

const linkClass =
  "inline-flex min-h-11 items-center rounded-md px-2 text-sm text-ink-600 hover:bg-ink-100 hover:text-ink-900";

/** Presentational: shown under every app and security screen. Gate health, the story and the source. */
export function AppFooter({ status }: { status: GateHealth }) {
  const s = STATUS[status];
  return (
    // Thyro floats in a bottom corner and lifts above this footer (useLiftAboveFooter).
    <footer id={APP_FOOTER_ID} className="mt-auto border-t border-ink-200 bg-white px-4 py-2">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6">
        <p
          role="status"
          className={`flex min-h-11 items-center gap-2 text-sm font-medium ${s.className}`}
        >
          <span aria-hidden="true">{s.glyph}</span>
          {s.text}
        </p>
        <nav aria-label="Footer" className="-mx-2 flex flex-wrap items-center sm:mx-0 sm:ml-auto">
          <Link to="/" className={linkClass}>
            About Pyli
          </Link>
          <a href={GITHUB} target="_blank" rel="noopener noreferrer" className={linkClass}>
            GitHub<span className="sr-only"> (opens in a new tab)</span>
          </a>
        </nav>
      </div>
    </footer>
  );
}
