import { Link } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { ArchitectureDiagram } from "./ArchitectureDiagram";
import { PageHead, SiteShell } from "./SiteShell";
import { LANDING_ONLY } from "./mode";

const FLOW: [string, string, string][] = [
  ["Paste", "Text or a file goes into an AI tool. Nothing has left the page yet.", "On the page"],
  [
    "Check 1, in the browser",
    "IDs, cards, IBANs and keys are found by rules. Instant, and it works with no network.",
    "In the browser",
  ],
  [
    "Check 2, on your server",
    "Reworded documents, names, code, tricks and memory across prompts.",
    "On your server",
  ],
  ["Policy", "Your rules for each team turn the findings into one decision.", "On your server"],
  ["Route", "Cloud AI, masked text, the local model, a question, or a stop.", "Browser or gateway"],
  [
    "Answer checked",
    "The reply is scanned too, and masked values are put back for the sender only.",
    "Back on the page",
  ],
];

const LAYERS: [string, string][] = [
  [
    "1 · Normalise",
    "Unicode NFKC, zero-width and direction characters removed, spaced digits joined, base64 and hex decoded. Each trick found is reported as a reason of its own.",
  ],
  [
    "2 · Patterns with checksums",
    "Greek tax number (mod 11), AMKA (valid date and Luhn), IBAN (mod 97), cards (Luhn). A random number does not trigger an alarm; a real one does.",
  ],
  [
    "3 · Secrets and code",
    "Key prefixes (sk-, AKIA, ghp_, xoxb-, AIza), private-key blocks, connection strings and company code markers by YARA rules. Source code by fingerprint.",
  ],
  [
    "4 · People and clients",
    "Names and phone numbers by Presidio with English and Greek language models. Your client list by accent-blind multi-word matching.",
  ],
  [
    "5 · Documents",
    "Registered documents are cut into overlapping 60-word pieces. MinHash finds near copies; multilingual embeddings in pgvector find reworded ones.",
  ],
  [
    "6 · Memory across prompts",
    "Which pieces of a restricted document one person has rebuilt in 24 hours. Past 40%, or three prompts on one document, it is blocked.",
  ],
  [
    "7 · Prompt injection",
    "A trained classifier plus known phrasings in English and Greek, applied to files, tool results and retrieved text before an agent reads them.",
  ],
  [
    "+ · Stamped files",
    "A file marked RESTRICTED, CONFIDENTIAL, INTERNAL USE ONLY or the Greek equivalents never leaves, whether or not it was registered.",
  ],
];

const DOUBLES: [string, string][] = [
  [
    "Two checks",
    "One in the browser, one on the server. The stricter answer wins. If the server cannot be reached, each kind of data has its own rule: fail open for the harmless, fail closed for keys and IDs.",
  ],
  [
    "Two ways to match",
    "Exact rules and checksums for things with a shape. Meaning, by embeddings, for text with none. Each covers what the other misses.",
  ],
  [
    "Two directions",
    "The question and the answer are both checked. A model that echoes a secret or carries an injected instruction is caught on the way back.",
  ],
  [
    "Two people",
    "Security sees a pseudonym. One person asks to reveal who it is, with a written reason. A different person must approve. Both steps are logged.",
  ],
  [
    "Two kinds of proof",
    "Decoy secrets planted in documents show which document leaked. Marked copies carry tiny differences, so a leaked copy points to the recipient it was made for.",
  ],
  [
    "Two stores, no text",
    "The database keeps a masked preview, the kind of data and the reason. The text is never stored, and records are deleted after 30 days.",
  ],
];

const TECHNIQUES: [string, string, string][] = [
  [
    "Input normalisation",
    "Evasion with spacing, hidden characters, look-alike letters and encoding",
    "Browser and server",
  ],
  ["Checksums", "False alarms on numbers that only look like IDs", "Browser and server"],
  ["YARA rules", "Keys, private-key blocks, connection strings, code markers", "Server"],
  [
    "MinHash and embeddings",
    "Copied and reworded confidential documents, in several languages",
    "Server",
  ],
  ["Session memory", "Leaking a document slice by slice", "Server"],
  ["Injection classifier", "Instructions hidden in files and tool results", "Server"],
  [
    "Output filtering",
    "Secrets echoed by a model, injected content in answers",
    "Gateway and server",
  ],
  [
    "Masking with restore",
    "Losing the answer while protecting the question",
    "Browser and gateway",
  ],
  ["Honeytokens", "Proving which document a leak came from", "Server"],
  ["Marked copies", "Tracing a leaked copy to its recipient", "Server"],
  ["Pseudonyms, two-person reveal", "Misuse of the monitoring tool itself", "Dashboard"],
  ["Append-only audit log", "Tampering and denial; the app role can only add and read", "Database"],
  ["Signed event export", "Forged or altered events sent to a SIEM (HMAC-SHA256)", "Server"],
  ["Retention limit", "Hoarding data that was never needed", "Database"],
  ["Self-hosting", "A third party reading what your people type", "Your Docker"],
];

const OUTCOMES: [string, string, string][] = [
  ["allow", "Allowed", "Goes through untouched."],
  ["warn", "Warned", "Asks the person to confirm and say why."],
  ["mask", "Masked", "Hides it, sends, restores in the answer."],
  ["local", "Answered locally", "A model on your servers answers."],
  ["block", "Blocked", "Stops it and offers a safe way."],
];

const LIMITS = [
  "Traffic that skips the gateway, such as personal devices, is outside what a server can see.",
  "A paraphrase that shares no words or topic with a registered document can pass.",
  "Retyping a document by hand, or photographing the screen, cannot be stopped. Marked copies only deter.",
  "Detection is probabilistic. Expect some false alarms and some misses; shadow mode measures both before anything is enforced.",
  "The demo has no login. A real pilot needs login, roles and TLS first.",
];

export default function DeepDive() {
  return (
    <SiteShell>
      <main id="main">
        <PageHead
          label="How it works"
          title="How Sentry works, end to end."
          lead="The design, the checks and the safeguards, in the order a message meets them."
        />

        <section className="section section-white" aria-labelledby="arch-h">
          <div className="wrap">
            <h2 id="arch-h">The system on one page.</h2>
            <ArchitectureDiagram />
          </div>
        </section>

        <section className="section" aria-labelledby="flow-title">
          <div className="wrap">
            <h2 id="flow-title">One message, six steps.</h2>
            <ol className="flow flow-6">
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
            <p className="prose">
              The cheapest check runs first and a clear block stops the rest. No step needs a paid
              AI model.
            </p>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="layers-h">
          <div className="wrap">
            <h2 id="layers-h">What the server looks for.</h2>
            <ul className="pair pair-4">
              {LAYERS.map(([t, d]) => (
                <li key={t} className="pair-card">
                  <h3>{t}</h3>
                  <p>{d}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="section" aria-labelledby="two-h">
          <div className="wrap">
            <h2 id="two-h">Two of everything that matters.</h2>
            <p className="section-sub">
              No single check is trusted alone. Each safeguard has a second one behind it.
            </p>
            <ul className="pair pair-3">
              {DOUBLES.map(([t, d]) => (
                <li key={t} className="pair-card">
                  <h3>{t}</h3>
                  <p>{d}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="out-title">
          <div className="wrap">
            <h2 id="out-title">Five outcomes, always with a reason.</h2>
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

        <section className="section" aria-labelledby="tech-h">
          <div className="wrap">
            <h2 id="tech-h">The security techniques, and what each one is for.</h2>
            <div className="tbl-scroll">
              <table className="tbl">
                <caption className="sr-only">Security techniques used by Sentry</caption>
                <thead>
                  <tr>
                    <th scope="col">Technique</th>
                    <th scope="col">What it defends against</th>
                    <th scope="col">Where</th>
                  </tr>
                </thead>
                <tbody>
                  {TECHNIQUES.map(([t, d, w]) => (
                    <tr key={t}>
                      <th scope="row">{t}</th>
                      <td>{d}</td>
                      <td>{w}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="section section-white" aria-labelledby="limits-h">
          <div className="wrap">
            <h2 id="limits-h">What it does not do.</h2>
            <ul className="watch">
              {LIMITS.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
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
