import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { CanvasFractalGrid } from "@/components/ui/canvas-fractal-grid";
import { PixelHeading } from "@/components/ui/pixel-heading-character";
import { RollingStat } from "@/components/ui/rolling-stat";
import { SecurityCheckpoint } from "@/components/ui/security-checkpoint";
import { useSeen } from "./Sections";
import { SiteShell } from "./SiteShell";
import { LANDING_ONLY } from "./mode";

/** A real answer from the brain for this message (POST /v1/check, tool Claude.ai). */
const TYPED: (string | [string, string])[] = [
  "Please wire 12,400 EUR to ",
  ["GR1601101250000000012300695", "IBAN"],
  " for ",
  ["Maria Papadopoulou", "NAME"],
];
const SENT = "Please wire 12,400 EUR to [IBAN_1] for [PERSON_1]";
const CHECKS: [string, string][] = [
  ["Your browser", "IBAN found · 2 ms"],
  ["Your server", "Name found · 9 ms"],
  ["Your rules", "Hide both · 1 ms"],
];

const OUTCOMES: [string, string, string][] = [
  ["allow", "Allowed", "Nothing sensitive. It goes as written."],
  ["warn", "Warned", "Looks sensitive. You confirm, or edit."],
  ["mask", "Masked", "Private values are swapped out, then restored in the answer."],
  ["local", "Answered locally", "A model on your servers answers. Nothing leaves."],
  ["block", "Blocked", "Stopped, with a reason and a safe way to still get your answer."],
];

const CATCHES: [string, string][] = [
  ["IDs, cards, IBANs", "GR16 0110 1250 …"],
  ["Secrets and keys", "sk-…  AKIA…  ghp_…"],
  ["People and clients", "Maria Papadopoulou"],
  ["Confidential documents", "Even reworded"],
  ["Stamped files", "ΕΜΠΙΣΤΕΥΤΙΚΟ · CONFIDENTIAL"],
  ["Hidden instructions", "“Ignore the rules above…”"],
];

const PROMISES: [string, string][] = [
  ["Never stores what you typed", "Only what was found, and what was done."],
  [
    "Names stay hidden",
    "Security sees a code. Revealing a person takes a reason and a second person.",
  ],
  ["Deleted after 30 days", "Every record, on a timer."],
  ["Runs on your servers", "No third party reads your prompts."],
];

const RECORD: [string, string][] = [
  ["When", "19 Nov, 09:14"],
  ["Who", "u-03ddf851 · Engineering"],
  ["Tool", "Claude"],
  ["Found", "IBAN GR••••••••0695"],
  ["Decision", "Masked"],
  ["Deleted", "in 30 days"],
];

const GITHUB = "https://github.com/alexkoukos/data-dna";
const START = `git clone ${GITHUB}
cd data-dna && docker compose up --build
# dashboard :3000  ·  API docs :8001/docs  ·  no API key`;
const CALL = `POST /v1/check  { "text": "…", "tool": "Claude.ai" }
→ { "action": "mask", "masked_text": "…[IBAN_1]…" }`;
const TESTS = "make check · make eval · make redteam · make e2e";

const LIMITS = [
  "Only ChatGPT, Claude and Gemini today.",
  "Text and stamped files. Not images.",
  "Demo data. A real pilot needs login first.",
];

export default function DeepDive() {
  const { hash } = useLocation();
  const [seenRef, seen] = useSeen<HTMLDivElement>();
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
  }, [hash]);
  return (
    <SiteShell>
      <main id="main" className="tight">
        <section className="page-head hero-dots" aria-labelledby="page-title">
          <CanvasFractalGrid
            contained
            className="[mask-image:linear-gradient(to_bottom,black_60%,transparent)]"
          />
          <div className="wrap">
            <PixelHeading
              as="h1"
              id="page-title"
              mode="wave"
              showLabel={false}
              className="font-normal"
            >
              How Sentry works.
            </PixelHeading>
            <p className="lead">Every message is checked before it leaves. This is what you see.</p>
          </div>
        </section>

        <section className="section" aria-labelledby="steps-h">
          <div className="wrap">
            <PixelHeading as="h2" id="steps-h" mode="multi" className="font-normal">
              Three steps. A tenth of a second.
            </PixelHeading>
            <ol className="steps3">
              <li className="step3">
                <span className="step3-n">1</span>
                <h3>You send</h3>
                <p className="ex-box">
                  {TYPED.map((p, i) =>
                    typeof p === "string" ? (
                      <span key={i}>{p}</span>
                    ) : (
                      <mark key={i} className="ex-hit">
                        {p[0]}
                        <small>{p[1]}</small>
                      </mark>
                    ),
                  )}
                </p>
              </li>
              <li className="step3">
                <span className="step3-n">2</span>
                <h3>Sentry checks</h3>
                <ul className="ex-checks">
                  {CHECKS.map(([who, what]) => (
                    <li key={who}>
                      <b>{who}</b>
                      <em>{what}</em>
                    </li>
                  ))}
                </ul>
              </li>
              <li className="step3">
                <span className="step3-n">3</span>
                <h3>The AI gets the safe version</h3>
                <p className="ex-box ex-out">{SENT}</p>
                <p className="ex-note">Your answer comes back with the real values put back.</p>
              </li>
            </ol>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="out-title">
          <div className="wrap">
            <PixelHeading as="h2" id="out-title" mode="multi" className="font-normal">
              Five things can happen.
            </PixelHeading>
            <ul className="oc-grid">
              {OUTCOMES.map(([k, name, text]) => (
                <li key={k} className={`oc ${k}`}>
                  <b>{name}</b>
                  <p>{text}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="section" aria-labelledby="catch-h">
          <div className="wrap">
            <PixelHeading as="h2" id="catch-h" mode="multi" className="font-normal">
              What it catches.
            </PixelHeading>
            <ul className="catch-chips">
              {CATCHES.map(([t, e]) => (
                <li key={t} title={e}>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="security" className="section section-white" aria-labelledby="sec-h">
          <div className="wrap">
            <PixelHeading as="h2" id="sec-h" mode="multi" className="font-normal">
              Your data stays yours.
            </PixelHeading>
            <div className="kept">
              <div className="kept-no dark">
                <SecurityCheckpoint
                  title="Sentry"
                  subtitle="Never stored"
                  message="What you typed is checked, then forgotten. Only the record on the right is kept."
                />
              </div>
              <div className="kept-yes">
                <h3>The only record</h3>
                <dl className="kept-rec">
                  {RECORD.map(([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>{v}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>
            <ul className="promises">
              {PROMISES.map(([t, d]) => (
                <li key={t}>
                  <b>{t}</b>
                  <span>{d}</span>
                </li>
              ))}
            </ul>
            <p className="be-aware">
              <b>Be aware:</b> {LIMITS.join(" ")}
            </p>
          </div>
        </section>

        <section id="developers" className="section" aria-labelledby="dev-h">
          <div className="wrap">
            <PixelHeading as="h2" id="dev-h" mode="multi" className="font-normal">
              Run it yourself.
            </PixelHeading>
            <div className="api-pair">
              <pre className="code" tabIndex={0} aria-label="Start">
                {START}
              </pre>
              <pre className="code" tabIndex={0} aria-label="One call">
                {CALL}
              </pre>
            </div>
            <p className="prose">
              Extension: <code>make extension-zip</code>. Tests: <code>{TESTS}</code>.
            </p>
            <div className="cta-row">
              <TextureButton asChild variant="primary" size="lg">
                <a href={GITHUB}>Open the repo</a>
              </TextureButton>
              {LANDING_ONLY ? null : (
                <TextureButton asChild variant="secondary" size="lg">
                  <Link to="/break-it">Try to break it</Link>
                </TextureButton>
              )}
            </div>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="proof-title">
          <div className="wrap">
            <PixelHeading as="h2" id="proof-title" mode="multi" className="font-normal">
              Measured. Misses published.
            </PixelHeading>
            <div className="stats" ref={seenRef}>
              <div className="stat">
                <strong>
                  <RollingStat value={seen ? 100 : 0} suffix="%" />
                </strong>
                <span>reworded leaks found. Regex: 5%</span>
              </div>
              <div className="stat">
                <strong>
                  <RollingStat value={seen ? 80 : 0} suffix=" / 80" />
                </strong>
                <span>attacks handled</span>
              </div>
              <div className="stat">
                <strong>
                  <RollingStat value={seen ? 12 : 0} suffix=" ms" />
                </strong>
                <span>added by the server check</span>
              </div>
              <div className="stat">
                <strong>2.1%</strong>
                <span>false alarms</span>
              </div>
            </div>
            <p className="prose">Invented data, tuned on that set. Read it as a ceiling.</p>
          </div>
        </section>
      </main>
    </SiteShell>
  );
}
