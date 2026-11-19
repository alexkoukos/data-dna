import { useEffect, useRef, useState } from "react";
import { MotionConfig } from "motion/react";
import { Database, FileLock2, ScanSearch } from "lucide-react";

import { CircuitBoard, type TechCardData } from "@/components/ui/circuit-board";
import { GatewayEndpoint } from "@/components/ui/gateway-endpoint-illustration";
import { PixelHeading } from "@/components/ui/pixel-heading-character";
import { RollingStat } from "@/components/ui/rolling-stat";
import { SecurityCheckpoint } from "@/components/ui/security-checkpoint";
import { fetchMetrics } from "@/lib/securityApi";

/** True once the element has been on screen, so numbers roll when people reach them. */
export function useSeen<T extends Element>() {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setSeen(true);
      return;
    }
    const io = new IntersectionObserver(
      ([e]) => {
        if (e?.isIntersecting) {
          setSeen(true);
          io.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return [ref, seen] as const;
}

/** The centre of the gateway drawing: the Sentry shield in its cell. */
const SentryMark = (
  <g data-slot="gateway-endpoint-sentry-mark">
    <path
      d="M132 44.5 L145 52 V68 L132 75.5 L119 68 V52 Z"
      fill="#1a1000"
      stroke="#f59e0b"
      strokeWidth="1.5"
      strokeLinejoin="round"
    />
    <image href="/brand/sentry-guard.svg" x="120.5" y="51.5" width="23" height="17.4" />
  </g>
);

const STEPS: [string, string][] = [
  ["Someone pastes or attaches.", "A prompt, a table, a PDF. Into any AI tool they already use."],
  [
    "Sentry checks it first.",
    "Names, IDs, keys, stamped files, and hidden instructions, in milliseconds.",
  ],
  [
    "It goes on, is masked, or stays inside.",
    "And there is always a way to still get the answer: the company AI reads what must not leave.",
  ],
];

const CARDS: TechCardData[] = [
  {
    name: "Presidio",
    href: "https://microsoft.github.io/presidio/",
    icon: <ScanSearch className="size-8" aria-hidden="true" />,
    description: "Finds names, phone numbers and IDs in the text, on your own server.",
    glowColor: "rgba(245, 158, 11, 0.15)",
  },
  {
    name: "YARA",
    href: "https://virustotal.github.io/yara/",
    icon: <FileLock2 className="size-8" aria-hidden="true" />,
    description:
      "Rules that catch keys, secrets and files stamped RESTRICTED or CONFIDENTIAL before they leave.",
    glowColor: "rgba(118, 74, 162, 0.15)",
  },
  {
    name: "pgvector + e5",
    href: "https://github.com/pgvector/pgvector",
    icon: <Database className="size-8" aria-hidden="true" />,
    description:
      "Recognises a confidential document even when it is reworded, shortened or translated.",
    glowColor: "rgba(0, 180, 216, 0.15)",
  },
];

/**
 * Explains the product as one piece: people's messages flow through the Sentry gate to the AI
 * tools, and below it the same gate shows the tools it runs on.
 */
export function HowItWorks() {
  return (
    <section id="how" className="section" aria-labelledby="how-title">
      <div className="wrap" data-reveal>
        <div className="how-grid">
          <div>
            <h2 id="how-title">One gate between your people and every AI tool.</h2>
            <ol className="how-steps">
              {STEPS.map(([title, text], i) => (
                <li key={title}>
                  <span className="how-num" aria-hidden="true">
                    {i + 1}
                  </span>
                  <div>
                    <strong>{title}</strong>
                    <p>{text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
          <figure className="how-fig">
            <GatewayEndpoint
              className="how-svg"
              logo={SentryMark}
              animated
              role="img"
              aria-label="Messages come in from the left, pass through the Sentry shield at the gate in the middle, and only what is safe goes on to ChatGPT, Claude, Grok and other AI tools on the right."
            />
            <figcaption>Everything passes the gate. Only what is safe goes on.</figcaption>
          </figure>
        </div>

        <div className="gate-link" aria-hidden="true" />

        <div className="powered">
          <h3 id="powered-title">The gate runs on tools your security team already trusts.</h3>
          <p className="section-sub">Open source, checkable, and running on your own server.</p>
          <MotionConfig reducedMotion="user">
            <CircuitBoard cards={CARDS} />
          </MotionConfig>
        </div>
      </div>
    </section>
  );
}

const FALLBACK = { checked: 11015, share: 91, stopped: 1431 };

/** What we solve, in three numbers that roll up when you reach them. */
export function Solved() {
  const [ref, seen] = useSeen<HTMLDivElement>();
  const [live, setLive] = useState(FALLBACK);
  useEffect(() => {
    let off = false;
    fetchMetrics()
      .then((m) => {
        if (off || !m.prompts_checked) return;
        setLive({
          checked: m.prompts_checked,
          share: Math.round((m.zero_llm_share ?? 0.91) * 100),
          stopped: m.incidents_7d,
        });
      })
      .catch(() => undefined); // the public page still tells its story with the demo numbers
    return () => {
      off = true;
    };
  }, []);
  const stats: [number, string, string, string?][] = [
    [live.checked, "prompts checked", "Every message, before it is sent."],
    [live.share, "handled without an AI model", "Fast checks, no tokens spent.", "%"],
    [live.stopped, "leaks stopped in a week", "Masked, kept in, or sent to the company AI."],
  ];
  return (
    <section className="section section-gray" aria-labelledby="solved-title">
      <div className="wrap" data-reveal>
        <PixelHeading as="h2" id="solved-title" mode="multi" className="font-normal">
          What Sentry is saving, in numbers.
        </PixelHeading>
        <p className="section-sub">
          People paste company data into AI tools every day. Sentry sees it first.
        </p>
        <div className="solved-grid" ref={ref}>
          {stats.map(([value, label, note, unit]) => (
            <div className="solved-card" key={label}>
              <p className="solved-num">
                <RollingStat value={seen ? value : 0} suffix={unit} />
              </p>
              <p className="solved-label">{label}</p>
              <p className="solved-note">{note}</p>
            </div>
          ))}
        </div>
        <p className="solved-fine">
          Based on the data of our mock company, created for this demo. The people and the numbers
          are invented.
        </p>
      </div>
    </section>
  );
}

/** The checkpoint every prompt stops at. */
export function Checkpoint() {
  return (
    <div className="checkpoint" data-reveal>
      <SecurityCheckpoint
        title="Sentry"
        subtitle="Security checkpoint"
        message="Every prompt stops here first. We check it before it reaches an AI tool."
      />
    </div>
  );
}
