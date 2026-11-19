import { Link, NavLink } from "react-router-dom";
import { Sentinel } from "@/components/Sentinel";
import "./landing.css";

const PAGES = [
  { to: "/how-it-works", label: "How it works" },
  { to: "/trust", label: "Security" },
  { to: "/developers", label: "Developers" },
];

/**
 * The glass navigation bar, used on every page of the site and the app. Few links on purpose: what it
 * is, what it catches, how it is built, who it is for. Everything inside the app is listed on /app.
 */
export function SiteNav() {
  return (
    <header className="top">
      <nav aria-label="Main" className="top-in">
        <Link to="/" className="top-logo" aria-label="Sentry home">
          <Sentinel size={30} className="top-mark" />
          <span className="top-word">Sentry</span>
        </Link>
        <div className="top-links">
          <NavLink
            to="/how-it-works"
            className={({ isActive }) => (isActive ? "is-here" : undefined)}
          >
            How it works
          </NavLink>
          {PAGES.slice(1).map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) => (isActive ? "is-here" : undefined)}
            >
              {l.label}
            </NavLink>
          ))}
          <NavLink to="/chat" className={({ isActive }) => (isActive ? "is-here" : undefined)}>
            Company AI
          </NavLink>
          <Link to="/app" className="btn btn-primary btn-sm">
            Live demo
          </Link>
        </div>
      </nav>
    </header>
  );
}
