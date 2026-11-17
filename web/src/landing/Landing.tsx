import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "@fontsource/plus-jakarta-sans/800.css";
import { Link } from "react-router-dom";
import "./landing.css";
import { HeroLoop } from "./HeroLoop";
import { PHASE } from "./loop";
import { Scaled } from "./Scaled";
import { OverviewMock } from "./OverviewMock";
import { Screen } from "./Screen";

const GITHUB = "https://github.com/alexkoukos/data-dna";

const STEPS = [
  {
    title: "Paste",
    body: "Someone drops a table, a key or a document into an AI tool, the way people do every day.",
    scene: 0,
    phase: PHASE.paste,
  },
  {
    title: "The bee checks",
    body: "Before anything is sent, the guard bee looks at the text, masks or stops what belongs to the hive, and says why.",
    scene: 1,
    phase: PHASE.bee,
  },
  {
    title: "You still get your answer",
    body: "Every block names a safe way forward, like Company AI, which can read it on your own servers.",
    scene: 3,
    phase: PHASE.card,
  },
];

type Kind = "mask" | "block" | "local" | "warn";
const CATCHES: { label: string; kind: Kind; word: string }[] = [
  { label: "Salaries", kind: "mask", word: "Masked" },
  { label: "IBAN", kind: "block", word: "Blocked" },
  { label: "AFM", kind: "block", word: "Blocked" },
  { label: "AMKA", kind: "block", word: "Blocked" },
  { label: "API keys", kind: "block", word: "Blocked" },
  { label: "Client names", kind: "mask", word: "Masked" },
  { label: "Source code", kind: "warn", word: "Warned" },
  { label: "Rewritten confidential documents", kind: "local", word: "Answered locally" },
  { label: "Prompt injection", kind: "block", word: "Blocked" },
];
const GLYPH: Record<Kind, string> = { mask: "◐", block: "■", local: "⌂", warn: "▲" };

const WATCHER = [
  ["Self-hosted.", "Runs in your own Docker setup, on your own servers."],
  ["No raw prompts stored.", "The log keeps what was found and what was done, not the text."],
  ["Masked previews only.", "Security teams see [SALARY_1], not the salary."],
  ["Two-person reveal.", "Seeing an original value needs a second person to approve."],
  ["An audit log.", "Every decision and every reveal is recorded."],
];

function Wordmark({ reverse = false, className = "" }: { reverse?: boolean; className?: string }) {
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

export default function Landing() {
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
          <div className="top-links">
            <a href="#how">How it works</a>
            <a href="#catches">What it catches</a>
            <a href="#security">For security teams</a>
            <Link to="/app" className="btn btn-primary btn-sm">
              Live demo
            </Link>
          </div>
        </nav>
      </header>

      <main id="main">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-in">
            <div className="hero-copy">
              <p className="eyebrow">Shadow AI protection</p>
              <h1 id="hero-title">Your data is the honey. We guard the gate.</h1>
              <p className="lead">
                Hive checks every prompt before it reaches an AI tool, masks or stops what belongs
                to your company, and always shows a way to still get your answer.
              </p>
              <div className="cta">
                <Link to="/app" className="btn btn-primary">
                  See the live demo
                </Link>
                <a href="#how" className="btn btn-secondary">
                  How it works
                </a>
              </div>
            </div>
            <HeroLoop />
          </div>
        </section>

        <section id="how" className="section section-white" aria-labelledby="how-title">
          <div className="wrap">
            <p className="eyebrow">How it works</p>
            <h2 id="how-title">Every prompt passes the gate.</h2>
            <ol className="steps">
              {STEPS.map((s, i) => (
                <li key={s.title} className="step">
                  <div className="step-frame" aria-hidden="true">
                    <Scaled width={720} height={450}>
                      <Screen still scene={s.scene} phase={s.phase} />
                    </Scaled>
                  </div>
                  <p className="step-n">Step {i + 1}</p>
                  <h3>{s.title}</h3>
                  <p>{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="catches" className="section" aria-labelledby="catches-title">
          <div className="wrap">
            <p className="eyebrow">What the bee catches</p>
            <h2 id="catches-title">The things people paste without thinking.</h2>
            <ul className="chips">
              {CATCHES.map((c) => (
                <li key={c.label} className="catch">
                  <span className="catch-label">{c.label}</span>
                  <span className={`chip chip-${c.kind}`}>
                    <span className="chip-icon" aria-hidden="true">
                      {GLYPH[c.kind]}
                    </span>
                    {c.word}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="security" className="section section-white" aria-labelledby="sec-title">
          <div className="wrap sec-grid">
            <div>
              <p className="eyebrow">For security teams</p>
              <h2 id="sec-title">One screen for the question you actually have.</h2>
              <p className="lead">
                The Overview counts saves, not violations. It shows which tools your teams use, what
                was kept in, and what needs a second look.
              </p>
              <Link to="/security" className="btn btn-secondary">
                Open the Overview
              </Link>
            </div>
            <figure className="shot">
              <div className="shot-frame">
                <div className="shot-bar" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </div>
                <OverviewMock />
              </div>
              <figcaption>
                Which teams sent client data to unapproved AI tools this week?
              </figcaption>
            </figure>
          </div>
        </section>

        <section className="section" aria-labelledby="watch-title">
          <div className="wrap">
            <p className="eyebrow">Who watches the watcher</p>
            <h2 id="watch-title">The gate is guarded too.</h2>
            <ul className="watch">
              {WATCHER.map(([title, text]) => (
                <li key={title}>
                  <strong>{title}</strong> {text}
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>

      <footer className="foot">
        <div className="wrap foot-in">
          <Wordmark className="foot-wordmark" />
          <p>Built for the Netcompany Hackathon 2026</p>
          <a href={GITHUB} className="foot-link">
            GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
