import { useEffect, useRef } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import "./GlassNav.css";

const LINKS = [
  { to: "/break-it", label: "Try to break it" },
  { to: "/chat", label: "Company AI" },
  { to: "/security", label: "Security" },
  { to: "/connect", label: "Connect a tool" },
];

/** The app's top bar. Same liquid glass as the public site; "Get the extension" is the one primary action. */
export function GlassNav() {
  const links = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();
  // On a phone the links scroll sideways: bring the current page into view.
  useEffect(() => {
    links.current
      ?.querySelector('[aria-current="page"]')
      ?.scrollIntoView?.({ inline: "center", block: "nearest" });
  }, [pathname]);
  return (
    <header className="gnav">
      <nav aria-label="Main" className="gnav-in">
        <Link to="/app" className="gnav-logo" aria-label="Hive home">
          <img src="/brand/hive-wordmark-reverse.svg" alt="Hive" width="173" height="70" />
        </Link>
        <div className="gnav-links" ref={links}>
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
