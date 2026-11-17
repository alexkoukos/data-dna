import { useEffect, useState } from "react";
import { OutcomeChip } from "../components/OutcomeChip";
import { ErrorPanel, Skeleton } from "../components/ui";
import {
  SAMPLES,
  createPairingCode,
  fetchDemoUsers,
  fetchSample,
  mockAiUrl,
  type Lang,
  type PairingCode,
} from "../lib/extensionApi";
import { useFetch } from "../lib/useFetch";

const btn =
  "inline-flex min-h-11 items-center justify-center rounded-md border border-ink-300 bg-white px-4 text-sm font-semibold text-ink-900 hover:bg-ink-100";

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="rounded-lg border border-ink-200 bg-white p-5">
      <h2 className="flex items-center gap-3 text-lg font-semibold text-ink-900">
        <span
          aria-hidden="true"
          className="flex size-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white"
        >
          {n}
        </span>
        <span>
          <span className="sr-only">Step {n}: </span>
          {title}
        </span>
      </h2>
      <div className="mt-3 max-w-prose space-y-2 text-ink-700">{children}</div>
    </li>
  );
}

function Pairing() {
  const [state, reload] = useFetch(fetchDemoUsers);
  const [user, setUser] = useState("");
  const [code, setCode] = useState<PairingCode | null>(null);
  const [failed, setFailed] = useState(false);

  if (state.status === "loading") return <Skeleton className="h-24" />;
  if (state.status === "error") return <ErrorPanel what="the demo people" onRetry={reload} />;
  const users = state.data;
  if (users.length === 0) {
    return (
      <p>
        Pairing codes are a demo feature and are off here. In a company, IT installs the extension
        and sets the person with a browser policy.
      </p>
    );
  }

  async function show() {
    setFailed(false);
    try {
      setCode(await createPairingCode(user));
    } catch {
      setCode(null);
      setFailed(true);
    }
  }

  return (
    <>
      <label htmlFor="who" className="block text-sm font-semibold text-ink-900">
        Pair as this person
      </label>
      <div className="flex flex-wrap gap-2">
        <select
          id="who"
          value={user}
          onChange={(e) => {
            setUser(e.target.value);
            setCode(null);
          }}
          className="min-h-11 min-w-0 flex-1 rounded-md border border-ink-300 bg-white px-3"
        >
          <option value="">Choose someone</option>
          {users.map((u) => (
            <option key={u.user} value={u.user}>
              {u.user} ({u.team})
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={show}
          disabled={!user}
          className={`${btn} disabled:opacity-50`}
        >
          Show pairing code
        </button>
      </div>
      {failed ? (
        <p role="alert" className="text-block-fg">
          We could not make a code. Try again in a moment.
        </p>
      ) : null}
      {code ? (
        <p role="status" className="rounded-md bg-ink-100 p-3">
          Type this in the extension&apos;s Settings:{" "}
          <strong className="font-mono text-2xl tracking-widest text-ink-900">{code.code}</strong>
          <span className="block text-sm text-ink-600">
            Works once, for {Math.round(code.expires_in / 60)} minutes. Incidents will show{" "}
            {code.user} from {code.team}.
          </span>
        </p>
      ) : null}
    </>
  );
}

function SampleCard({ id, lang }: { id: string; lang: Lang }) {
  const meta = SAMPLES.find((s) => s.id === id)!;
  const [text, setText] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let live = true;
    fetchSample(id, lang).then(
      (t) => live && setText(t),
      () => live && setText(""),
    );
    return () => {
      live = false;
    };
  }, [id, lang]);

  async function copy() {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard can be blocked; the text is visible and can be selected by hand.
    }
  }

  return (
    <li className="rounded-lg border border-ink-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold text-ink-900">{meta.title}</h3>
        <OutcomeChip outcome={meta.outcome} />
      </div>
      <p className="mt-1 text-sm text-ink-600">{meta.shows}</p>
      {text === null ? (
        <Skeleton className="mt-3 h-16" />
      ) : text === "" ? (
        <p className="mt-3 text-sm text-ink-600">
          The sample files are not served here. Open samples/{lang}/{meta.id}.txt in the repository.
        </p>
      ) : (
        <>
          <pre
            lang={lang}
            className="mt-3 whitespace-pre-wrap break-words rounded-md bg-ink-50 p-3 text-sm text-ink-900"
          >
            {text}
          </pre>
          <button type="button" onClick={copy} className={`${btn} mt-2`}>
            {copied ? "Copied" : `Copy ${meta.title.toLowerCase()}`}
          </button>
        </>
      )}
    </li>
  );
}

/** Container: download the extension, install it, pair it, then try the five outcomes. */
export default function ExtensionPage() {
  const [lang, setLang] = useState<Lang>("en");
  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <p className="eyebrow">Pyli</p>
      <h1 className="text-3xl font-semibold text-ink-900">Get the extension</h1>
      <p className="mt-2 max-w-prose text-ink-600">
        The extension sits in Chrome, right where people paste into ChatGPT, Claude or Gemini. It
        checks the text before it is sent and tells the person what it did and why.
      </p>

      <ol className="mt-6 space-y-4">
        <Step n={1} title="Download it">
          <a
            href="/extension.zip"
            download="pyli-extension.zip"
            className="inline-flex min-h-11 items-center rounded-md bg-brand-600 px-5 text-base font-semibold text-white hover:bg-brand-700"
          >
            Download pyli-extension.zip
          </a>
        </Step>

        <Step n={2} title="Install it in Chrome">
          <ol className="list-decimal space-y-1 pl-5">
            <li>Unzip the file into a folder.</li>
            <li>
              Open <code className="rounded bg-ink-100 px-1">chrome://extensions</code> and turn on
              Developer mode (top right).
            </li>
            <li>Choose Load unpacked and select the folder.</li>
          </ol>
          <p className="text-sm text-ink-600">
            In a company this step does not exist: IT installs it for everyone with a Chrome policy
            (an example is in <code className="rounded bg-ink-100 px-1">deploy/</code>).
          </p>
        </Step>

        <Step n={3} title="Pair it (demo)">
          <Pairing />
        </Step>

        <Step n={4} title="Try it on the demo chat">
          <a href={mockAiUrl()} target="_blank" rel="noreferrer" className={btn}>
            Open the demo chat (opens a new tab)
          </a>
          <p>Paste each text below into the chat and watch what happens.</p>
          <div role="group" aria-label="Language of the samples" className="flex gap-2">
            {(["en", "el"] as const).map((l) => (
              <button
                key={l}
                type="button"
                aria-pressed={lang === l}
                onClick={() => setLang(l)}
                className={`min-h-11 rounded-md border px-3 text-sm font-medium ${lang === l ? "border-brand-600 bg-brand-50 text-brand-700" : "border-ink-300 bg-white text-ink-700 hover:bg-ink-100"}`}
              >
                {l === "en" ? "English" : "Ελληνικά"}
              </button>
            ))}
          </div>
        </Step>
      </ol>

      <ul className="mt-4 space-y-3" aria-label="Sample texts">
        {SAMPLES.map((s) => (
          <SampleCard key={`${s.id}-${lang}`} id={s.id} lang={lang} />
        ))}
      </ul>
    </main>
  );
}
