import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "@fontsource/plus-jakarta-sans/800.css";
import type { ReactNode } from "react";
import { SiteNav } from "./SiteNav";
import "./landing.css";

/** The navigation bar shared by every public page. */
export function SiteShell({ children }: { children: ReactNode; home?: boolean }) {
  return (
    <div className="sentry">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <SiteNav />
      {children}
    </div>
  );
}

/** Top of a text page: small label, headline, one lead sentence. */
export function PageHead({ title, lead }: { label?: string; title: string; lead: string }) {
  return (
    <section className="page-head" aria-labelledby="page-title">
      <div className="wrap">
        <h1 id="page-title">{title}</h1>
        <p className="lead">{lead}</p>
      </div>
    </section>
  );
}
