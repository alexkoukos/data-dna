import { Link } from "react-router-dom";
import { AppCard } from "../components/AppCard";
import { Sentinel } from "../components/Sentinel";

const TOOLS = [
  {
    to: "/extension",
    name: "Get the extension",
    text: "Install it in Chrome.",
    points: ["Checks paste, send and files", "ChatGPT, Claude and Gemini", "Connects by itself"],
    cta: "Install it",
  },
  {
    to: "/break-it",
    name: "Try to break it",
    text: "Paste something risky and watch.",
    points: ["Hide data any way you like", "See which check caught it", "Report what got through"],
    cta: "Try it",
  },
  {
    to: "/chat",
    name: "Company AI",
    text: "Ask the model that never leaves your server.",
    points: [
      "Every message checked first",
      "Attach PDF, Word or images",
      "Private data stays masked",
    ],
    cta: "Open the chat",
  },
  {
    to: "/security",
    name: "Security",
    text: "Incidents, policies and proof.",
    points: [
      "Every decision with a reason",
      "Policies you can try first",
      "A compliance report (PDF)",
    ],
    cta: "Open the security view",
  },
  {
    to: "/connect",
    name: "Connect a tool",
    text: "Send events from your own tools.",
    points: ["Get a personal key", "One OpenAI-compatible address", "See it connect live"],
    cta: "Connect",
  },
];

/** Presentational: the front door. One primary action (start the demo), the story in three steps. */
export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <section className="flex flex-wrap items-center gap-8">
        <div className="min-w-0 flex-1 basis-80">
          <h1 className="mt-2 text-4xl font-semibold text-ink-900 sm:text-5xl">
            Use AI at work without leaking company data.
          </h1>
          <p className="mt-4 max-w-prose text-lg text-ink-600">
            Sentry is a browser extension and a dashboard. It checks what people paste into AI
            chats, masks or stops private data, and shows your security team which AI tools are
            really used.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              to="/extension"
              className="inline-flex min-h-11 items-center rounded-md bg-brand-600 px-5 text-base font-semibold text-[#1a1000] hover:bg-brand-500"
            >
              Get the extension
            </Link>
            <Link
              to="/security"
              className="inline-flex min-h-11 items-center rounded-md px-2 text-sm font-semibold text-brand-700 underline"
            >
              Or jump to the security view
            </Link>
          </div>
        </div>
        <div className="mx-auto">
          <Sentinel size={112} />
        </div>
      </section>

      <section aria-labelledby="tools-h" className="mt-12">
        <h2 id="tools-h" className="text-lg font-semibold text-ink-900">
          Everything in the app
        </h2>
        <ul className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {TOOLS.map((t) => (
            <li key={t.to}>
              <AppCard {...t} />
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
