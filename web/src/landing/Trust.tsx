import { Link } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { PageHead, SiteShell } from "./SiteShell";

/** What a person typed, and the only record that exists afterwards. Same example as /how-it-works. */
const RECORD: [string, string][] = [
  ["When", "19 Nov, 09:14"],
  ["Who", "u-03ddf851 (a pseudonym), Engineering"],
  ["Tool", "Claude"],
  ["Found", "IBAN GR••••••••••••••••••0695"],
  ["Decision", "Masked"],
  ["Why", "Contains iban, person"],
  ["Deleted", "in 30 days"],
];

const RULES: [string, string, string][] = [
  [
    "No raw prompts",
    "Only what was found and what was done is stored.",
    "A test sends prompts through every outcome, then searches every table for the original text.",
  ],
  [
    "Pseudonyms",
    "Security sees u-03ddf851, not a name.",
    "Revealing needs a written reason and a different person to approve.",
  ],
  [
    "Audit log",
    "Reveals, policy edits and setting changes are recorded.",
    "Append-only: the app role can add and read, not edit.",
  ],
  [
    "Expiry",
    "Incidents delete after 30 days.",
    "Set with RETENTION_DAYS. Raise it if a rule needs longer.",
  ],
  [
    "Self-hosted",
    "Docker on your servers, with a local model.",
    "Nothing is sent to a third party for checking.",
  ],
];

const LIMITS = [
  "Only the sites the extension is set up for: ChatGPT, Claude and Gemini.",
  "Typed and pasted text, and stamped files. Images and the text inside scans are not read.",
  "The demo has no login. A real pilot needs login, roles and TLS first.",
  "Every result so far is on invented data.",
];

export default function Trust() {
  return (
    <SiteShell>
      <main id="main">
        <PageHead
          label="Security and privacy"
          title="The gate is guarded too."
          lead="A tool that reads what people type has to follow its own rules."
        />

        <section className="section section-white" aria-labelledby="rec-title">
          <div className="wrap">
            <h2 id="rec-title">What is kept about a message.</h2>
            <div className="kept">
              <div className="kept-no">
                <h3>Never stored</h3>
                <p className="ex-box kept-typed">
                  Please wire 12,400 EUR to GR1601101250000000012300695 for Maria Papadopoulou…
                </p>
                <p className="ex-note">The text a person typed, and the real values in it.</p>
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
          </div>
        </section>

        <section className="section" aria-labelledby="p-title">
          <div className="wrap">
            <h2 id="p-title">Five rules, and how each is enforced.</h2>
            <div className="tbl-scroll">
              <table className="tbl">
                <caption className="sr-only">Privacy rules and how each is enforced</caption>
                <thead>
                  <tr>
                    <th scope="col">Rule</th>
                    <th scope="col">What it means</th>
                    <th scope="col">Enforced by</th>
                  </tr>
                </thead>
                <tbody>
                  {RULES.map(([t, d, e]) => (
                    <tr key={t}>
                      <th scope="row">{t}</th>
                      <td>{d}</td>
                      <td>{e}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="l-title">
          <div className="wrap">
            <h2 id="l-title">Honest limits.</h2>
            <ul className="watch">
              {LIMITS.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
            <div className="cta-row">
              <TextureButton asChild variant="secondary" size="lg">
                <Link to="/developers">See how it is built</Link>
              </TextureButton>
            </div>
          </div>
        </section>
      </main>
    </SiteShell>
  );
}
