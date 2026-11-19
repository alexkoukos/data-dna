import { Link } from "react-router-dom";
import { TextureButton } from "@/components/ui/texture-button";
import { HeroLoop } from "./HeroLoop";
import { Catches } from "./Landing";
import { HeroBackdrop } from "./HeroBackdrop";
import { SiteShell } from "./SiteShell";

const STEPS = [
  { t: "Check", d: "Every prompt is scanned before it reaches an AI tool." },
  { t: "Mask or block", d: "Company data is replaced or stopped. Nothing leaves the hive." },
  { t: "Still get an answer", d: "Company AI answers locally, so there is always a way out." },
];

/** Scaffold of the new landing page: Apple Glass nav (SiteShell), dot-field hero with only the screen on the right. */
export default function LandingV2() {
  return (
    <SiteShell home>
      <main id="main">
        <section className="hero" aria-labelledby="v2-title">
          <HeroBackdrop className="hero-ribbon" />
          <div className="hero-in">
            <div className="hero-copy">
              <h1 id="v2-title">Your data stays yours. Sentry holds the gate.</h1>
              <p className="lead">
                Sentry checks every prompt before it reaches an AI tool, masks or stops what belongs
                to your company, and always shows a way to still get your answer.
              </p>
              <div className="cta">
                <TextureButton asChild variant="primary">
                  <Link to="/app">Live demo</Link>
                </TextureButton>
                <TextureButton asChild variant="secondary">
                  <a href="#how">How it works</a>
                </TextureButton>
              </div>
            </div>
            <HeroLoop />
          </div>
        </section>

        <section id="how" className="section" aria-labelledby="how-title">
          <div className="wrap">
            <h2 id="how-title">How it works</h2>
            <ol className="v2-steps">
              {STEPS.map((s, i) => (
                <li key={s.t}>
                  <strong>
                    {i + 1}. {s.t}
                  </strong>
                  <p>{s.d}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="catches" className="section section-white" aria-labelledby="catches-title">
          <div className="wrap">
            <h2 id="catches-title">What it catches</h2>
            <Catches />
          </div>
        </section>

        <section id="security" className="section" aria-labelledby="sec-title">
          <div className="wrap">
            <h2 id="sec-title">For security teams</h2>
            <p className="lead">
              Incidents, policies, a review queue and an audit trail. Sentry names data types, never
              values.
            </p>
            <TextureButton asChild variant="secondary">
              <Link to="/security">Open the dashboard</Link>
            </TextureButton>
          </div>
        </section>

        <section id="extension" className="section section-white" aria-labelledby="ext-title">
          <div className="wrap">
            <h2 id="ext-title">The browser extension</h2>
            <p className="lead">The sentinel sits on ChatGPT and checks before you send.</p>
            <TextureButton asChild variant="secondary">
              <Link to="/extension">Get the extension</Link>
            </TextureButton>
          </div>
        </section>

        <section className="section" aria-labelledby="final-title">
          <div className="wrap">
            <h2 id="final-title">See it guard the gate</h2>
            <div className="cta">
              <TextureButton asChild variant="primary">
                <Link to="/app">Live demo</Link>
              </TextureButton>
              <TextureButton asChild variant="secondary">
                <Link to="/break-it">Try to break it</Link>
              </TextureButton>
            </div>
          </div>
        </section>
      </main>
    </SiteShell>
  );
}
