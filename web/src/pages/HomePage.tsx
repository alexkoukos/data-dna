import { Link } from "react-router-dom";
import { Sentinel } from "../components/Sentinel";

const TOOLS = [
  { to: "/extension", name: "Get the extension", text: "Install it in Chrome." },
  { to: "/break-it", name: "Try to break it", text: "Paste something risky and watch." },
  { to: "/chat", name: "Company AI", text: "Ask the model that never leaves your server." },
  { to: "/security", name: "Security", text: "Incidents, policies and proof." },
  { to: "/connect", name: "Connect a tool", text: "Send events from your own tools." },
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
        <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {TOOLS.map((t) => (
            <li key={t.to}>
              <Link
                to={t.to}
                className="flex h-full min-h-11 flex-col rounded-lg border border-ink-200 bg-surface p-4 hover:border-brand-600"
              >
                <span className="font-semibold text-ink-900">{t.name}</span>
                <span className="mt-1 text-sm text-ink-600">{t.text}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
