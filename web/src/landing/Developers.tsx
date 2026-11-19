import { Link } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { PageHead, SiteShell } from "./SiteShell";

const GITHUB = "https://github.com/alexkoukos/data-dna";

const PARTS: [string, string][] = [
  ["Extension", "Chrome and Edge. WXT, TypeScript."],
  ["Brain :8001", "FastAPI, Pydantic v2, SQLAlchemy 2."],
  ["Dashboard :3000", "React, TypeScript, Tailwind v4."],
  ["Database", "Postgres 16 with pgvector."],
];

const API = [
  "POST /v1/check",
  "POST /v1/events",
  "GET  /v1/policy",
  "POST /v1/pair",
  "POST /v1/ask-local",
  "POST /v1/logs/ingest",
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
            <pre className="code" tabIndex={0}>{`git clone ${GITHUB}
cd data-dna
docker compose up --build`}</pre>
            <p className="prose">
              Dashboard on <code>localhost:3000</code>, API docs on <code>localhost:8001/docs</code>
              . Extension: <code>make extension</code>, then load the folder unpacked.
            </p>
          </div>
        </section>

        <section className="section" aria-labelledby="parts-title">
          <div className="wrap">
            <h2 id="parts-title">Inside.</h2>
            <div className="pair pair-4">
              {PARTS.map(([t, d]) => (
                <div key={t} className="pair-card">
                  <h3>{t}</h3>
                  <p>{d}</p>
                </div>
              ))}
            </div>
            <p className="prose">
              Optional: <code>make gateway</code> puts SDKs and agents behind the same checks.{" "}
              <code>make local</code> adds a local model.
            </p>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="api-title">
          <div className="wrap">
            <h2 id="api-title">The extension's API.</h2>
            <pre className="code" tabIndex={0}>
              {API.join("\n")}
            </pre>
            <p className="prose">
              Browser rules are shared JSON, tested by both Python and TypeScript on the same
              fixtures.
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
