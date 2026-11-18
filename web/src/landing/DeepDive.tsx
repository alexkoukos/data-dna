import { Link } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { PageHead, SiteShell } from "./SiteShell";

const FLOW: [string, string, string][] = [
  ["Paste", "Text or a file goes into an AI tool.", "On the page"],
  ["Browser check", "IDs, cards, IBANs, keys. Instant, works offline.", "In the browser"],
  [
    "Deep check",
    "Reworded documents, names, code, tricks, memory across prompts.",
    "On your server",
  ],
  ["Policy", "Your rules per team decide what happens.", "On your server"],
  ["Outcome", "One of five, always with a reason.", "Back on the page"],
];

const OUTCOMES: [string, string, string][] = [
  ["allow", "Allowed", "Goes through untouched."],
  ["warn", "Warned", "Asks the person to confirm."],
  ["mask", "Masked", "Hides it, sends, restores in the answer."],
  ["local", "Answered locally", "A model on your servers answers."],
  ["block", "Blocked", "Stops it and offers a safe way."],
];

export default function DeepDive() {
  return (
    <SiteShell>
      <main id="main">
        <PageHead
          label="Deep dive"
          title="The second after you paste."
          lead="Cheapest check first. A clear decision at the end. Never a dead end."
        />

        <section className="section section-white" aria-labelledby="flow-title">
          <div className="wrap">
            <h2 id="flow-title">Five steps, one second.</h2>
            <ol className="flow">
              {FLOW.map(([title, text, where], i) => (
                <li key={title} className="flow-step">
                  <span className="flow-n" aria-hidden="true">
                    {i + 1}
                  </span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                  <span className="flow-where">{where}</span>
                </li>
              ))}
            </ol>
            <p className="prose">No step needs a paid AI model.</p>
          </div>
        </section>

        <section className="section" aria-labelledby="out-title">
          <div className="wrap">
            <h2 id="out-title">Five outcomes.</h2>
            <ul className="outcomes">
              {OUTCOMES.map(([k, name, text]) => (
                <li key={k} className={`outcome ${k}`}>
                  <b>{name}</b>
                  <p>{text}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="only-title">
          <div className="wrap">
            <h2 id="only-title">What a regex can't do.</h2>
            <div className="pair">
              <div className="pair-card">
                <h3>Reworded documents</h3>
                <p>A memo rewritten in someone's own words is still recognised.</p>
              </div>
              <div className="pair-card">
                <h3>Pieces over time</h3>
                <p>Three prompts that add up to 60% of a memo get stopped.</p>
              </div>
              <div className="pair-card">
                <h3>Who leaked it</h3>
                <p>
                  Marked copies name the source. The person stays hidden until two people approve.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="section" aria-labelledby="proof-title">
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
              <TextureButton asChild variant="primary" size="lg">
                <Link to="/break-it">Try to break it</Link>
              </TextureButton>
              <TextureButton asChild variant="secondary" size="lg">
                <Link to="/developers">For developers</Link>
              </TextureButton>
            </div>
          </div>
        </section>
      </main>
    </SiteShell>
  );
}
