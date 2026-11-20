import { Link } from "react-router-dom";
import { Sentinel } from "@/components/Sentinel";
import { useGateHealth, type GateHealth } from "@/lib/healthApi";
import "./landing.css";
import { LANDING_ONLY } from "./mode";

const GITHUB = "https://github.com/alexkoukos/data-dna";

const PRODUCT: [string, string][] = [
  ["How it works", "/how-it-works"],
  ["Get the extension", "/extension"],
];
const APP: [string, string][] = [
  ["Live demo", "/app"],
  ["Company AI", "/chat"],
  ["Security dashboard", "/security"],
  ["Try to break it", "/break-it"],
  ["Connect a tool", "/connect"],
];

// Text and glyph carry the meaning; the color only repeats it.
const STATUS: Record<GateHealth, { glyph: string; text: string }> = {
  checking: { glyph: "…", text: "Checking the gate" },
  online: { glyph: "●", text: "Gate online" },
  degraded: { glyph: "▲", text: "Gate online, database unreachable. Run make up." },
  offline: { glyph: "■", text: "Gate offline. Start it with make up." },
};

/** Live gate health. Not shown on the public site, which has no brain behind it. */
function GateStatus() {
  const status = useGateHealth();
  const s = STATUS[status];
  return (
    <p role="status" className={`sfoot-status sfoot-status-${status}`}>
      <span aria-hidden="true">{s.glyph}</span>
      {s.text}
    </p>
  );
}

/** The footer on every page: the logo and every page, one click away. */
export function SiteFooter() {
  return (
    <footer className="sfoot">
      <div className="sfoot-in">
        <div className="sfoot-brand">
          <Link to="/" className="sfoot-logo" aria-label="Sentry home">
            <Sentinel size={28} />
            <span>Sentry</span>
          </Link>
          <p>Your data stays yours. Sentry holds the gate.</p>
          {LANDING_ONLY ? null : <GateStatus />}
        </div>
        <nav aria-label="Footer" className="sfoot-cols">
          <div>
            <h2>Product</h2>
            <ul>
              {PRODUCT.filter(([, to]) => !(LANDING_ONLY && to === "/extension")).map(([t, to]) => (
                <li key={to}>
                  <Link to={to}>{t}</Link>
                </li>
              ))}
            </ul>
          </div>
          {LANDING_ONLY ? null : (
            <div>
              <h2>The app</h2>
              <ul>
                {APP.map(([t, to]) => (
                  <li key={to}>
                    <Link to={to}>{t}</Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div>
            <h2>Code</h2>
            <ul>
              <li>
                <a href={GITHUB} target="_blank" rel="noreferrer">
                  GitHub
                </a>
              </li>
              <li>
                <Link to="/how-it-works#developers">Run it yourself</Link>
              </li>
            </ul>
          </div>
        </nav>
      </div>
    </footer>
  );
}
