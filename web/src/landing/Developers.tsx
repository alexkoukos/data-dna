import { Link } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { PageHead, SiteShell } from "./SiteShell";

const GITHUB = "https://github.com/alexkoukos/data-dna";

const START = `$ docker compose up --build
 ✔ Container sentry-db-1       Healthy
 ✔ Container sentry-vault-a-1  Healthy
 ✔ Container sentry-brain-1    Healthy
 ✔ Container sentry-web-1      Healthy
Web: http://localhost:3000   Brain API: http://localhost:8001/docs`;

/** A real call and the real answer (demo data). */
const REQUEST = `POST /v1/check
{ "text": "Please wire 12,400 EUR to GR1601101250000000012300695 for Maria Papadopoulou",
  "tool": "Claude.ai", "url": "https://claude.ai/new" }`;

const RESPONSE = `{ "action": "mask",
  "reasons": ["Contains iban", "Contains person email phone"],
  "findings": [{ "entity": "IBAN", "masked_preview": "GR••••••••••••••••••0695" }],
  "masked_text": "Please wire 12,400 EUR to [IBAN_1] for [PERSON_1]" }`;

const PARTS: [string, string][] = [
  ["Extension", "WXT, React, TypeScript. Chrome, Edge, Brave."],
  ["Brain :8001", "FastAPI, Pydantic v2, SQLAlchemy 2."],
  ["Dashboard :3000", "React, Tailwind v4."],
  ["Database", "Postgres 16, pgvector."],
];

export default function Developers() {
  return (
    <SiteShell>
      <main id="main">
        <PageHead
          label="Developers"
          title="Run it. Read it. Test it."
          lead="One command, invented data, no API key."
        />

        <section className="section section-white" aria-labelledby="run-title">
          <div className="wrap">
            <h2 id="run-title">Start.</h2>
            <pre className="code term" tabIndex={0}>{`git clone ${GITHUB}
cd data-dna
${START}`}</pre>
            <p className="prose">
              No API key and invented data. Extension: <code>make extension-zip</code>, then load{" "}
              <code>extension/.output/chrome-mv3</code> unpacked.
            </p>
          </div>
        </section>

        <section className="section" aria-labelledby="api-title">
          <div className="wrap">
            <h2 id="api-title">One call.</h2>
            <div className="api-pair">
              <pre className="code" tabIndex={0} aria-label="Request">
                {REQUEST}
              </pre>
              <pre className="code" tabIndex={0} aria-label="Response">
                {RESPONSE}
              </pre>
            </div>
            <p className="prose">
              Also <code>/v1/events</code>, <code>/v1/policy</code>, <code>/v1/pair</code>,{" "}
              <code>/v1/ask-local</code>. Browser rules are shared JSON, tested by Python and
              TypeScript on the same fixtures. Full reference at <code>:8001/docs</code>.
            </p>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="parts-title">
          <div className="wrap">
            <h2 id="parts-title">Inside.</h2>
            <dl className="parts">
              {PARTS.map(([t, d]) => (
                <div key={t}>
                  <dt>{t}</dt>
                  <dd>{d}</dd>
                </div>
              ))}
            </dl>
            <p className="prose">
              <code>make gateway</code> puts SDKs and agents behind the same checks.{" "}
              <code>make local</code> adds a local model.
            </p>
          </div>
        </section>

        <section className="section" aria-labelledby="test-title">
          <div className="wrap">
            <h2 id="test-title">Prove it.</h2>
            <pre className="code" tabIndex={0}>{`make check     # lint, types, unit tests
make eval      # accuracy vs baseline
make redteam   # attack prompts
make e2e       # browser tests`}</pre>
            <div className="cta-row">
              <TextureButton asChild variant="primary" size="lg">
                <a href={GITHUB}>Open the repo</a>
              </TextureButton>
              <TextureButton asChild variant="secondary" size="lg">
                <Link to="/trust">Security and privacy</Link>
              </TextureButton>
            </div>
          </div>
        </section>
      </main>
    </SiteShell>
  );
}
