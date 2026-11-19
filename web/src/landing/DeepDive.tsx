import { Link } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { ArchitectureDiagram } from "./ArchitectureDiagram";
import { PageHead, SiteShell } from "./SiteShell";
import { LANDING_ONLY } from "./mode";

/** A real answer from the brain for this message (POST /v1/check, tool Claude.ai). */
const EXAMPLE = {
  typed: [
    "Please wire 12,400 EUR to ",
    ["GR1601101250000000012300695", "IBAN"],
    " for ",
    ["Maria Papadopoulou", "PERSON"],
    ", then send her the contract.",
  ] as (string | [string, string])[],
  sent: "Please wire 12,400 EUR to [IBAN_1] for [PERSON_1], then send her the contract.",
  checks: [
    ["Browser rules", "IBAN, mod 97 valid", "2 ms"],
    ["Server check", "Name found by Presidio", "9 ms"],
    ["Policy", "IBAN and person: mask", "1 ms"],
  ] as [string, string, string][],
};

const OUTCOMES: [string, string, string, string][] = [
  ["allow", "Allowed", "Nothing sensitive in it.", "Sent as written"],
  [
    "warn",
    "Warned",
    "Looks like a Greek ID number. Confirm before it goes.",
    "Send anyway · Edit message",
  ],
  [
    "mask",
    "Masked",
    "1 item masked before sending. Real values come back in the answer.",
    "Sent with [IBAN_1]",
  ],
  [
    "local",
    "Answered locally",
    "Company AI can answer this without it leaving.",
    "Ask the company AI",
  ],
  [
    "block",
    "Blocked",
    "This file is marked RESTRICTED and must stay inside the company.",
    "Open company AI · Edit message",
  ],
];

/** What the server looks for, with a real example of each and how it tells. */
const CHECKS: [string, string, string][] = [
  [
    "IDs, cards, IBANs",
    "GR16 0110 1250 0000 0001 2300 695",
    "Checksums (mod 97, Luhn, mod 11). A random number does not trigger.",
  ],
  [
    "Secrets and code",
    "sk-…, AKIA…, ghp_…, private-key blocks",
    "Prefix rules (YARA); source code by fingerprint.",
  ],
  [
    "People and clients",
    "Maria Papadopoulou, a client list",
    "Presidio in English and Greek; accent-blind matching.",
  ],
  [
    "Documents",
    "A reworded paragraph of a confidential report",
    "60-word pieces, MinHash for copies, embeddings for rewording.",
  ],
  [
    "Slice by slice",
    "Three prompts that rebuild one document",
    "Per-person memory for 24 h. Past 40% of a document, it is blocked.",
  ],
  [
    "Stamped files",
    "A PDF marked ΕΜΠΙΣΤΕΥΤΙΚΟ or CONFIDENTIAL",
    "The marking is read from the file. It never leaves.",
  ],
  [
    "Hidden instructions",
    "“Ignore previous instructions…” inside a file",
    "A trained classifier plus known phrasings, before an agent reads it.",
  ],
  [
    "Tricks",
    "1 2 3 4 5 6 7 8 3, zero-width characters, base64",
    "Normalised first; each trick found is a reason of its own.",
  ],
];

/** One line each: what stops it going wrong. */
const SAFEGUARDS: string[] = [
  "Two checks, browser and server. The stricter wins. Server down: keys and IDs fail closed, harmless text fails open.",
  "The answer is checked too. A secret echoed by the model is caught on the way back.",
  "Security sees a pseudonym. Revealing a person needs a reason and a second person. Both are logged.",
  "The text is never stored: a masked preview, the kind of data and the reason, for 30 days.",
  "The audit log is append-only. The app can add and read, not edit.",
  "Decoy secrets in documents show which one leaked. Self-hosted, so no third party reads prompts.",
];

const LIMITS = [
  "Traffic that skips the gateway, such as personal devices, is outside what a server can see.",
  "A paraphrase that shares no words or topic with a registered document can pass.",
  "Retyping a document by hand, or photographing the screen, cannot be stopped.",
  "Detection is probabilistic. Shadow mode measures false alarms and misses before anything is enforced.",
  "The demo has no login. A real pilot needs login, roles and TLS first.",
];

export default function DeepDive() {
  return (
    <SiteShell>
      <main id="main">
        <PageHead
          label="How it works"
          title="How Sentry works, end to end."
          lead="What happens to a message between Enter and the AI."
        />

        <section className="section section-white" aria-labelledby="arch-h">
          <div className="wrap">
            <h2 id="arch-h">The system on one page.</h2>
            <ArchitectureDiagram />
          </div>
        </section>

        <section className="section" aria-labelledby="ex-h">
          <div className="wrap">
            <h2 id="ex-h">One real message.</h2>
            <p className="section-sub">
              Typed into Claude. The cheapest check runs first, and a clear block stops the rest.
            </p>
            <div className="ex" role="group" aria-label="A message, the checks, and what is sent">
              <div className="ex-col">
                <h3>1 · What was typed</h3>
                <p className="ex-box">
                  {EXAMPLE.typed.map((p, i) =>
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
              </div>
              <div className="ex-col">
                <h3>2 · What checked it</h3>
                <ul className="ex-checks">
                  {EXAMPLE.checks.map(([who, what, t]) => (
                    <li key={who}>
                      <b>{who}</b>
                      <span>{what}</span>
                      <em>{t}</em>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="ex-col">
                <h3>3 · What the AI receives</h3>
                <p className="ex-box ex-out">{EXAMPLE.sent}</p>
                <p className="ex-note">
                  The answer comes back with the real values restored, on that page only.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="out-title">
          <div className="wrap">
            <h2 id="out-title">Five outcomes. Each says why.</h2>
            <ul className="oc-grid">
              {OUTCOMES.map(([k, name, text, act]) => (
                <li key={k} className={`oc ${k}`}>
                  <b>{name}</b>
                  <p>{text}</p>
                  <span>{act}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="section" aria-labelledby="layers-h">
          <div className="wrap">
            <h2 id="layers-h">What it looks for.</h2>
            <div className="tbl-scroll">
              <table className="tbl">
                <caption className="sr-only">
                  What the checks look for, with an example and the method
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Looks for</th>
                    <th scope="col">Example</th>
                    <th scope="col">How</th>
                  </tr>
                </thead>
                <tbody>
                  {CHECKS.map(([t, e, h]) => (
                    <tr key={t}>
                      <th scope="row">{t}</th>
                      <td>{e}</td>
                      <td>{h}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="two-h">
          <div className="wrap">
            <h2 id="two-h">Safeguards.</h2>
            <ul className="watch">
              {SAFEGUARDS.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="section" aria-labelledby="limits-h">
          <div className="wrap">
            <h2 id="limits-h">What it does not do.</h2>
            <ul className="watch">
              {LIMITS.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="proof-title">
          <div className="wrap">
            <h2 id="proof-title">Measured, with the misses published.</h2>
            <div className="stats">
              <div className="stat">
                <strong>100%</strong>
                <span>reworded leaks found. Regex: 5%</span>
              </div>
              <div className="stat">
                <strong>2.1%</strong>
                <span>false alarms</span>
              </div>
              <div className="stat">
                <strong>12 ms</strong>
                <span>added by the server check</span>
              </div>
              <div className="stat">
                <strong>80 / 80</strong>
                <span>attacks handled, in two sets</span>
              </div>
            </div>
            <p className="prose">Invented data, tuned on that set. Read it as a ceiling.</p>
            <div className="cta-row">
              {LANDING_ONLY ? null : (
                <TextureButton asChild variant="primary" size="lg">
                  <Link to="/break-it">Try to break it</Link>
                </TextureButton>
              )}
              <TextureButton asChild variant={LANDING_ONLY ? "primary" : "secondary"} size="lg">
                <Link to="/developers">For developers</Link>
              </TextureButton>
            </div>
          </div>
        </section>
      </main>
    </SiteShell>
  );
}
