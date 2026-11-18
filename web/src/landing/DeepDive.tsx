import { Link } from "react-router-dom";
import { PageHead, SiteShell } from "./SiteShell";

const LAYERS = [
  [
    "In the browser, instantly",
    "The extension checks what you paste or send on ChatGPT, Claude and Gemini before it leaves the page. It catches Greek tax and social security numbers, IBANs, cards, emails, phones and keys, using checksums so look-alikes are not flagged. It works offline too.",
  ],
  [
    "On your server, in depth",
    "Hive's brain adds the checks that need more context: look-alike letters, Greeklish, hidden characters, people and client names, source code and secrets, and prompt-injection phrases.",
  ],
  [
    "Confidential documents, even reworded",
    "Registered documents are fingerprinted and compared by shape and by meaning, so a paragraph rewritten in someone's own words is still recognised, and the right copy is named.",
  ],
  [
    "Memory across prompts",
    "If someone sends a memo in three pieces, Hive adds them up. At 60% of a document already sent, the next piece is stopped.",
  ],
  [
    "Your policy decides",
    "Findings meet a policy table per team. Policies can be tried on the last 14 days before saving, or run in shadow mode that records what would have happened and changes nothing.",
  ],
];

const OUTCOMES: [string, string, string][] = [
  ["allow", "Allowed", "Nothing sensitive. It goes through untouched."],
  ["warn", "Warned", "Asks the person to confirm, with the reason in plain words."],
  ["mask", "Masked", "Hides the sensitive part, sends it, and puts it back in the answer."],
  ["local", "Answered locally", "A model on your own servers answers, so the data never leaves."],
  ["block", "Blocked", "Stops it, says why, and points to an approved alternative."],
];

export default function DeepDive() {
  return (
    <SiteShell>
      <main id="main">
        <PageHead
          label="Deep dive"
          title="What happens in the second after you paste."
          lead="Cheapest check first, a clear decision at the end, and never a dead end for the person typing."
        />

        <section className="section section-white" aria-labelledby="layers-title">
          <div className="wrap">
            <h2 id="layers-title">Five layers, cheapest first.</h2>
            <p className="prose">
              Most prompts are settled by the first layer. Nothing here needs a paid model: every
              prompt is checked without spending a single AI token.
            </p>
            <ol className="layers">
              {LAYERS.map(([title, text]) => (
                <li key={title} className="layer">
                  <div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="section" aria-labelledby="out-title">
          <div className="wrap">
            <h2 id="out-title">Five outcomes. Always with a reason.</h2>
            <p className="prose">
              Every decision is shown as a word and an icon, never colour alone, with what happened
              and what to do next.
            </p>
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

        <section className="section section-white" aria-labelledby="see-title">
          <div className="wrap">
            <h2 id="see-title">Seeing the tools nobody approved.</h2>
            <p className="prose">
              The extension notes which AI tool a prompt went to, counts only and never text.
              Network usage logs add the tools that nobody installed anything for. Together they
              fill the AI tools list with each tool marked approved, tolerated or unapproved, and
              the approved alternative to suggest.
            </p>
            <p className="prose">
              For your most important documents, every recipient can receive a copy with small
              harmless differences. If a piece leaks, Hive names the copy it came from. The person
              behind it stays hidden until two people approve.
            </p>
          </div>
        </section>

        <section className="section" aria-labelledby="proof-title">
          <div className="wrap">
            <h2 id="proof-title">How we know it works.</h2>
            <p className="prose">
              A labelled set of 195 invented prompts in Greek and English, two attack sets of 80,
              and a regex baseline for comparison. The expected answer is written before the result
              is looked at, and misses are published.
            </p>
            <div className="stats">
              <div className="stat">
                <strong>100%</strong>
                <span>reworded document leaks found (40 of 40, regex baseline 5%)</span>
              </div>
              <div className="stat">
                <strong>2.1%</strong>
                <span>false alarms on clean prompts</span>
              </div>
              <div className="stat">
                <strong>12 ms</strong>
                <span>median time added by the server check</span>
              </div>
              <div className="stat">
                <strong>80 / 80</strong>
                <span>attacks handled in each of two attack sets</span>
              </div>
            </div>
            <p className="prose">
              The document figure was tuned on that set, so read it as a ceiling. Greek clean
              prompts raise more false alarms than English ones. The full tables are in the repo.
            </p>
            <div className="cta-row">
              <Link to="/break-it" className="btn btn-primary">
                Try to break it
              </Link>
              <Link to="/developers" className="btn btn-secondary">
                For developers
              </Link>
            </div>
          </div>
        </section>
      </main>
    </SiteShell>
  );
}
