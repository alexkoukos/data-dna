import { Link } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { PageHead, SiteShell } from "./SiteShell";

const PROMISES: [string, string][] = [
  ["No raw prompts", "We keep what was found and what was done, not your text."],
  ["Masked previews", "Security sees [SALARY_1], never the salary."],
  ["Two-person reveal", "One asks with a reason. A different person approves."],
  ["Full audit log", "Every reveal, policy edit and setting change."],
  ["30-day expiry", "Incidents delete themselves."],
  ["Self-hosted", "Your Docker, your servers, your local model."],
];

const LIMITS = [
  "It covers the sites the extension is set up for.",
  "Typed and pasted text only. No images or file contents yet.",
  "The demo has no login. A real pilot needs one.",
  "All results so far are on invented data.",
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

        <section className="section section-white" aria-labelledby="p-title">
          <div className="wrap">
            <h2 id="p-title">Six promises. Each one has a test.</h2>
            <ul className="pair pair-3">
              {PROMISES.map(([t, d]) => (
                <li key={t} className="pair-card">
                  <h3>{t}</h3>
                  <p>{d}</p>
                </li>
              ))}
            </ul>
            <p className="prose">
              A test sends prompts through every outcome and searches every table for the original
              text. It fails if any is found.
            </p>
          </div>
        </section>

        <section className="section" aria-labelledby="l-title">
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
