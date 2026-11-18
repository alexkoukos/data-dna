import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "@fontsource/plus-jakarta-sans/800.css";
import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import "./landing.css";

const GITHUB = "https://github.com/alexkoukos/data-dna";

export function Wordmark({
  reverse = false,
  className = "",
}: {
  reverse?: boolean;
  className?: string;
}) {
  return (
    <img
      className={className}
      src={reverse ? "/brand/hive-wordmark-reverse.svg" : "/brand/hive-wordmark.svg"}
      alt="Hive"
      width="173"
      height="70"
    />
  );
}

const LINKS = [
  { to: "/how-it-works", label: "Deep dive" },
  { to: "/trust", label: "Security and privacy" },
  { to: "/developers", label: "Developers" },
];

/** Header and footer shared by every public page. The app has its own chrome. */
export function SiteShell({ children, home = false }: { children: ReactNode; home?: boolean }) {
  return (
    <div className="hive">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="top">
        <nav aria-label="Main" className="top-in">
          <Link to="/" className="top-logo" aria-label="Hive home">
            <Wordmark className="top-wordmark" />
          </Link>
          {home ? (
            <div className="top-links">
              <a href="#how">How it works</a>
              <a href="#catches">What it catches</a>
              <a href="#security">For security teams</a>
              <Link to="/app" className="btn btn-primary btn-sm">
                Live demo
              </Link>
            </div>
          ) : (
            <div className="top-links">
              {LINKS.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  className={({ isActive }) => (isActive ? "is-here" : undefined)}
                >
                  {l.label}
                </NavLink>
              ))}
              <Link to="/app" className="btn btn-primary btn-sm">
                Open the app
              </Link>
            </div>
          )}
        </nav>
      </header>
      {children}
      <footer className="foot">
        <div className="wrap foot-in">
          <Wordmark className="foot-wordmark" />
          <p>Built for the Netcompany Hackathon 2026</p>
          <nav aria-label="Footer" className="foot-nav">
            {LINKS.map((l) => (
              <Link key={l.to} to={l.to} className="foot-link">
                {l.label}
              </Link>
            ))}
            <a href={GITHUB} className="foot-link">
              GitHub
            </a>
          </nav>
        </div>
      </footer>
    </div>
  );
}

/** Top of a text page: small label, headline, one lead sentence. */
export function PageHead({ label, title, lead }: { label: string; title: string; lead: string }) {
  return (
    <section className="page-head" aria-labelledby="page-title">
      <div className="wrap">
        <p className="page-label">{label}</p>
        <h1 id="page-title">{title}</h1>
        <p className="lead">{lead}</p>
      </div>
    </section>
  );
}
