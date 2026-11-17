import { Link } from "react-router-dom";
import { Thyro } from "../components/Thyro";

const STEPS = [
  {
    n: 1,
    title: "An employee pastes something risky",
    body: "A bank account number, an access key, a client name. The kind of thing people paste into ChatGPT without thinking. The extension is right there in the browser.",
    to: "/extension",
    cta: "Get the extension",
  },
  {
    n: 2,
    title: "Pyli catches it before it is sent",
    body: "Each message is checked before it leaves the browser. It is allowed, masked, held for a second look, answered by the company AI or blocked, with the reason in plain words.",
    to: "/break-it",
    cta: "Try to break it",
  },
  {
    n: 3,
    title: "Security sees it, with proof",
    body: "Every decision becomes an incident. Names stay sealed until a second person approves. Ask questions and get a table plus the SQL behind it.",
    to: "/security/incidents",
    cta: "Open the security view",
  },
];

/** Presentational: the front door. One primary action (start the demo), the story in three steps. */
export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <section className="flex flex-wrap items-center gap-8">
        <div className="min-w-0 flex-1 basis-80">
          <p className="eyebrow">Pyli, the gate</p>
          <h1 className="mt-2 text-4xl font-semibold text-ink-900 sm:text-5xl">
            Use AI at work without leaking company data.
          </h1>
          <p className="mt-4 max-w-prose text-lg text-ink-600">
            Pyli is a browser extension and a dashboard. It checks what people paste into AI chats,
            masks or stops private data, and shows your security team which AI tools are really
            used.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              to="/extension"
              className="inline-flex min-h-11 items-center rounded-md bg-brand-600 px-5 text-base font-semibold text-white hover:bg-brand-700"
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
          <Thyro pose="master" size={280} />
        </div>
      </section>

      <section aria-labelledby="how-h" className="mt-14">
        <h2 id="how-h" className="text-lg font-semibold text-ink-900">
          How the demo goes
        </h2>
        <ol className="mt-4 grid gap-4 md:grid-cols-3">
          {STEPS.map((s) => (
            <li key={s.n} className="flex flex-col rounded-lg border border-ink-200 bg-white p-5">
              <span
                aria-hidden="true"
                className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white"
              >
                {s.n}
              </span>
              <h3 className="mt-3 font-semibold text-ink-900">
                <span className="sr-only">Step {s.n}: </span>
                {s.title}
              </h3>
              <p className="mt-1 flex-1 text-sm text-ink-600">{s.body}</p>
              <Link
                to={s.to}
                className="mt-4 inline-flex min-h-11 items-center text-sm font-semibold text-brand-700 underline"
              >
                {s.cta}
              </Link>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
