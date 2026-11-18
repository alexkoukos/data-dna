import { Link } from "react-router-dom";
import { PageHead, SiteShell } from "./SiteShell";

const CLAIMS: [string, string][] = [
  ["No raw prompts stored.", "Incidents keep the kind of data found, the reason and a masked preview. A test sends prompts through every outcome and searches every table for the original text."],
  ["Masked previews only.", "Security teams read [SALARY_1], not the salary."],
  ["Two-person reveal.", "To see who is behind an incident, one person asks with a reason and a different person approves."],
  ["Everything is audited.", "Reveal steps, policy edits, setting changes and decoy triggers all go in the audit log, never with the values."],
  ["Incidents expire.", "They are deleted after 30 days by default."],
  ["Shadow mode is logged.", "Switching between recording and enforcing is itself recorded."],
  ["Split storage for the most sensitive fields.", "A value is stored as two shares in two separate databases. A dump of either one is random noise."],
];

const LIMITS = [
  "The browser extension covers the sites it is set up for. A person can remove it, and Hive tells you when a device stops reporting.",
  "Only typed and pasted text is checked. Images and file uploads are not.",
  "The demo has no login yet, so reviewers are typed names. A login is needed before a real pilot.",
  "Everything measured so far is on invented data. No customer has been interviewed.",
];

export default function Trust() {
  return (
    <SiteShell>
      <main id="main">
        <PageHead
          label="Security and privacy"
          title="The gate is guarded too."
          lead="A tool that reads what people type must hold itself to the rules it enforces."
        />

        <section className="section section-white" aria-labelledby="claims-title">
          <div className="wrap">
            <h2 id="claims-title">What Hive keeps, and what it does not.</h2>
            <ul className="watch">
              {CLAIMS.map(([title, text]) => (
                <li key={title}>
                  <strong>{title}</strong> {text}
                </li>
              ))}
            </ul>
            <p className="prose">
              Each claim points at the code and a test that fails if the claim stops being true.
            </p>
          </div>
        </section>

        <section className="section" aria-labelledby="where-title">
          <div className="wrap">
            <h2 id="where-title">Where it runs.</h2>
            <p className="prose">
              Self-hosted, in your own Docker setup. The local model that answers confidential
              questions runs on your own servers, so those prompts never leave. Ports are open on
              localhost only, and the server starts as a non-root user.
            </p>
            <p className="prose">
              A plain-language page covers GDPR, NIS2 and the EU AI Act, and the dashboard can
              export a PDF that maps what Hive does to each. It supports your own review and is not
              legal advice.
            </p>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="limits-title">
          <div className="wrap">
            <h2 id="limits-title">Honest limits.</h2>
            <ul className="watch">
              {LIMITS.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
            <div className="cta-row">
              <Link to="/developers" className="btn btn-secondary">
                Read how it is built
              </Link>
            </div>
          </div>
        </section>
      </main>
    </SiteShell>
  );
}
