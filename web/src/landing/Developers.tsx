import { Link } from "react-router-dom";
import { PageHead, SiteShell } from "./SiteShell";

const GITHUB = "https://github.com/alexkoukos/data-dna";

const PARTS: [string, string, string][] = [
  ["Extension", "Chrome and Edge, Manifest V3", "WXT and TypeScript. Checks paste and send in the page, with all site selectors in adapters."],
  ["Brain", "port 8001", "FastAPI, Pydantic v2, SQLAlchemy 2. Detection, policy, incidents, analyst questions. API docs at /docs."],
  ["Dashboard", "port 3000", "React, TypeScript and Tailwind v4. Also serves the extension zip."],
  ["Database", "internal", "Postgres 16 with pgvector, seeded with an invented company."],
  ["Demo chat", "port 3100", "A small ChatGPT-like page for the offline demo and the tests."],
];

const API: [string, string][] = [
  ["POST /v1/check", "Browser check result in, final decision out."],
  ["POST /v1/events", "Telemetry. Counts and tool names, no text."],
  ["GET /v1/policy", "The policy, with an ETag so the extension can cache it."],
  ["POST /v1/pair", "Pair a device with a 6-digit code."],
  ["POST /v1/ask-local", "Ask the local model for the company-AI outcome."],
  ["POST /v1/logs/ingest", "Proxy and DNS logs for tools nobody installed anything for."],
];

export default function Developers() {
  return (
    <SiteShell>
      <main id="main">
        <PageHead
          label="Developers"
          title="Run it, read it, test it."
          lead="One command starts the whole stack with invented data. No API key is needed for the demo."
        />

        <section className="section section-white" aria-labelledby="run-title">
          <div className="wrap">
            <h2 id="run-title">Start in two minutes.</h2>
            <pre className="code">{`git clone ${GITHUB}
cd data-dna
docker compose up --build`}</pre>
            <p className="prose">
              Needs Docker with Compose v2 and about 2 GB of free RAM. Open{" "}
              <code>localhost:3000</code> for the dashboard and <code>localhost:8001/docs</code> for
              the API. To build the extension yourself, run <code>make extension</code> and load{" "}
              <code>extension/.output/chrome-mv3</code> unpacked.
            </p>
          </div>
        </section>

        <section className="section" aria-labelledby="parts-title">
          <div className="wrap">
            <h2 id="parts-title">What is in the box.</h2>
            <div className="tbl-scroll">
              <table className="tbl">
                <thead>
                  <tr>
                    <th scope="col">Part</th>
                    <th scope="col">Where</th>
                    <th scope="col">What it is</th>
                  </tr>
                </thead>
                <tbody>
                  {PARTS.map(([a, b, c]) => (
                    <tr key={a}>
                      <th scope="row">{a}</th>
                      <td>{b}</td>
                      <td>{c}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="prose">
              An optional LiteLLM gateway, <code>make gateway</code>, puts SDKs, agents and Claude
              Code behind the same checks. A local model, <code>make local</code>, answers the
              company-AI outcome with real text.
            </p>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="api-title">
          <div className="wrap">
            <h2 id="api-title">The API the extension uses.</h2>
            <div className="tbl-scroll">
              <table className="tbl">
                <thead>
                  <tr>
                    <th scope="col">Endpoint</th>
                    <th scope="col">What it does</th>
                  </tr>
                </thead>
                <tbody>
                  {API.map(([a, b]) => (
                    <tr key={a}>
                      <th scope="row">
                        <code>{a}</code>
                      </th>
                      <td>{b}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="prose">
              Fixtures for the browser rules are shared, so the Python and TypeScript sides are
              tested against the same cases. To roll the extension out to a whole company, an example
              Chrome policy is in <code>deploy/</code>.
            </p>
          </div>
        </section>

        <section className="section" aria-labelledby="test-title">
          <div className="wrap">
            <h2 id="test-title">Prove it yourself.</h2>
            <pre className="code">{`make check      # lint, types and unit tests
make eval       # accuracy against the baseline, misses listed
make loadtest   # latency under load
make redteam    # curated attack prompts
make e2e        # browser tests`}</pre>
            <p className="prose">
              The brain has about 380 tests, the dashboard 76 and the extension 36. Every number on
              this site comes from one of these commands. The repo also holds the product spec, the
              threat model and the evidence map for the hackathon brief.
            </p>
            <div className="cta-row">
              <a href={GITHUB} className="btn btn-primary">
                Open the repo
              </a>
              <Link to="/trust" className="btn btn-secondary">
                Security and privacy
              </Link>
            </div>
          </div>
        </section>
      </main>
    </SiteShell>
  );
}
