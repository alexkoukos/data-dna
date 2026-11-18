import { Link, NavLink } from "react-router-dom";
import "./GlassNav.css";

const LINKS = [
  { to: "/break-it", label: "Try to break it" },
  { to: "/chat", label: "Company AI" },
  { to: "/security", label: "Security" },
  { to: "/connect", label: "Connect a tool" },
];

/** The app's top bar. Same liquid glass as the public site; "Get the extension" is the one primary action. */
export function GlassNav() {
  return (
    <header className="gnav">
      <nav aria-label="Main" className="gnav-in">
        <Link to="/app" className="gnav-logo" aria-label="Hive home">
          <img src="/brand/hive-wordmark-reverse.svg" alt="Hive" width="173" height="70" />
        </Link>
        <div className="gnav-links">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to}>
              {l.label}
            </NavLink>
          ))}
          <NavLink to="/extension" className="gnav-cta">
            Get the extension
          </NavLink>
        </div>
      </nav>
    </header>
  );
}
