/**
 * The whole system on one picture: where a message goes, which checks it passes, and what is stored.
 * Plain SVG so it stays sharp and readable. The dashes on the arrows move to show the direction of
 * travel; they stop for people who ask for reduced motion.
 */
export function ArchitectureDiagram() {
  return (
    <figure className="arch">
      <svg
        viewBox="0 0 980 470"
        role="img"
        aria-labelledby="arch-title arch-desc"
        className="arch-svg"
      >
        <title id="arch-title">How Sentry is built</title>
        <desc id="arch-desc">
          A message leaves the browser or an SDK, passes the browser check, then the brain's seven
          checks and the policy. It goes on to a cloud AI, a local model or is blocked. Every answer
          is checked on the way back. Only masked records are written to the database.
        </desc>
        <defs>
          <marker
            id="arch-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M0 0 L10 5 L0 10 z" fill="#f59e0b" />
          </marker>
        </defs>

        {/* Browser */}
        <g>
          <rect x="16" y="50" width="260" height="190" rx="16" className="arch-box" />
          <text x="34" y="80" className="arch-title">
            Browser
          </text>
          <rect x="34" y="96" width="224" height="48" rx="10" className="arch-chip" />
          <text x="46" y="117" className="arch-t">
            AI chat page
          </text>
          <text x="46" y="134" className="arch-s">
            ChatGPT · Claude · Gemini
          </text>
          <rect x="34" y="156" width="224" height="68" rx="10" className="arch-accent" />
          <text x="46" y="178" className="arch-t-dark">
            Sentry extension · check 1
          </text>
          <text x="46" y="196" className="arch-s-dark">
            IDs, cards, IBANs, keys
          </text>
          <text x="46" y="212" className="arch-s-dark">
            Instant, works offline
          </text>
        </g>

        {/* Gateway */}
        <g>
          <rect x="16" y="288" width="260" height="110" rx="16" className="arch-box" />
          <text x="34" y="318" className="arch-title">
            Gateway
          </text>
          <text x="34" y="340" className="arch-t">
            SDKs · agents · Claude Code
          </text>
          <text x="34" y="360" className="arch-s">
            Personal keys, one door for code
          </text>
          <text x="34" y="378" className="arch-s">
            Checks the answer on the way back
          </text>
        </g>

        {/* Brain */}
        <g>
          <rect x="360" y="40" width="270" height="300" rx="16" className="arch-box arch-box-hot" />
          <text x="378" y="70" className="arch-title">
            Brain · check 2
          </text>
          <text x="378" y="88" className="arch-s">
            Your server, no paid AI model
          </text>
          {[
            "1  Normalise: tricks undone",
            "2  Patterns with checksums",
            "3  Secrets, names, code",
            "4  Documents, even reworded",
            "5  Memory across prompts",
            "6  Prompt injection",
            "7  Policy per team",
          ].map((t, i) => (
            <g key={t}>
              <rect x="378" y={104 + i * 32} width="234" height="26" rx="8" className="arch-chip" />
              <text x="390" y={122 + i * 32} className="arch-t">
                {t}
              </text>
            </g>
          ))}
        </g>

        {/* Database */}
        <g>
          <rect x="360" y="370" width="270" height="84" rx="16" className="arch-box" />
          <text x="378" y="398" className="arch-title">
            Postgres + pgvector
          </text>
          <text x="378" y="418" className="arch-s">
            Masked incidents, never the text
          </text>
          <text x="378" y="434" className="arch-s">
            Fingerprints · append-only audit log
          </text>
        </g>

        {/* Outcomes */}
        <g>
          <rect x="714" y="40" width="250" height="100" rx="16" className="arch-box" />
          <text x="732" y="70" className="arch-title">
            Cloud AI
          </text>
          <text x="732" y="92" className="arch-t">
            Allowed or masked text only
          </text>
          <text x="732" y="112" className="arch-s">
            Real values return in the answer,
          </text>
          <text x="732" y="128" className="arch-s">
            on the page of the person who asked
          </text>

          <rect x="714" y="170" width="250" height="100" rx="16" className="arch-box" />
          <text x="732" y="200" className="arch-title">
            Local model · Company AI
          </text>
          <text x="732" y="222" className="arch-t">
            Sensitive questions stay inside
          </text>
          <text x="732" y="242" className="arch-s">
            Runs on your own servers
          </text>

          <rect x="714" y="300" width="250" height="100" rx="16" className="arch-box" />
          <text x="732" y="330" className="arch-title">
            Blocked or asked first
          </text>
          <text x="732" y="352" className="arch-t">
            Always with a reason in words
          </text>
          <text x="732" y="372" className="arch-s">
            And a safe way to still get the answer
          </text>
        </g>

        {/* Arrows */}
        <g className="arch-flow" fill="none" markerEnd="url(#arch-arrow)">
          <path d="M276 160 C 316 160, 320 150, 356 150" />
          <path d="M276 340 C 316 340, 320 250, 356 250" />
          <path d="M630 90 C 670 90, 676 90, 710 90" />
          <path d="M630 190 C 670 190, 676 220, 710 220" />
          <path d="M630 290 C 670 290, 676 350, 710 350" />
          <path d="M495 342 L 495 366" />
        </g>
        <text x="282" y="136" className="arch-lbl">
          text, files
        </text>
        <text x="632" y="82" className="arch-lbl">
          safe
        </text>
        <text x="632" y="180" className="arch-lbl">
          private
        </text>
        <text x="632" y="282" className="arch-lbl">
          stop
        </text>
      </svg>
      <figcaption>
        A message passes two checks, one in the browser and one on your server, before anything
        leaves. Answers are checked on the way back too.
      </figcaption>
    </figure>
  );
}
