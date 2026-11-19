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
import { ExtensionTerminal, INSTALL_TABS, OUTCOME_TABS } from "../components/ExtensionTerminal";
import { TextureButton } from "@/components/ui/texture-button";
import { Check, Copy, ExternalLink, KeyRound } from "lucide-react";

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="rounded-lg border border-ink-200 bg-surface p-5">
      <h2 className="flex items-center gap-3 text-lg font-semibold text-ink-900">
        <span
          aria-hidden="true"
          className="flex size-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-[#1a1000]"
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
          className="min-h-11 min-w-0 flex-1 rounded-md border border-ink-300 bg-surface px-3"
        >
          <option value="">Choose someone</option>
          {users.map((u) => (
            <option key={u.user} value={u.user}>
              {u.user} ({u.team})
            </option>
          ))}
        </select>
        <TextureButton variant="secondary" type="button" onClick={show} disabled={!user}>
          <KeyRound className="size-4" aria-hidden="true" />
          Show pairing code
        </TextureButton>
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
    <li className="rounded-lg border border-ink-200 bg-surface p-4">
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
          <TextureButton variant="secondary" type="button" onClick={copy} className="mt-2">
            {copied ? (
              <Check className="size-4" aria-hidden="true" />
            ) : (
              <Copy className="size-4" aria-hidden="true" />
            )}
            {copied ? "Copied" : `Copy ${meta.title.toLowerCase()}`}
          </TextureButton>
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
      <h1 className="text-3xl font-semibold text-ink-900">Get the extension</h1>
      <p className="mt-2 max-w-prose text-ink-600">
        The extension sits in Chrome, right where people paste into ChatGPT, Claude or Gemini. It
        checks the text before it is sent and tells the person what it did and why.
      </p>

      <ol className="mt-6 space-y-4">
        <Step n={1} title="Download it">
          <a
            href="/extension.zip"
            download="sentry-extension.zip"
            className="inline-flex min-h-11 items-center rounded-md bg-brand-600 px-5 text-base font-semibold text-[#1a1000] hover:bg-brand-500"
          >
            Download sentry-extension.zip
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
          <ExtensionTerminal
            tabs={INSTALL_TABS}
            label="The commands to download and install the extension, one tab for each"
            className="pt-2"
          />
          <p className="text-sm text-ink-600">
            In a company this step does not exist: IT installs it for everyone with a Chrome policy
            (an example is in <code className="rounded bg-ink-100 px-1">deploy/</code>).
          </p>
        </Step>

        <Step n={3} title="Pair it (demo)">
          <Pairing />
        </Step>

        <Step n={4} title="Try it on the demo chat">
          <TextureButton variant="secondary" asChild>
            <a href={mockAiUrl()} target="_blank" rel="noreferrer">
              Open the demo chat (opens a new tab)
              <ExternalLink className="size-4" aria-hidden="true" />
            </a>
          </TextureButton>
          <p>Paste each text below into the chat and watch what happens.</p>
          <div role="group" aria-label="Language of the samples" className="flex gap-2">
            {(["en", "el"] as const).map((l) => (
              <TextureButton
                key={l}
                type="button"
                aria-pressed={lang === l}
                onClick={() => setLang(l)}
                variant={lang === l ? "primary" : "secondary"}
              >
                {l === "en" ? "English" : "Ελληνικά"}
              </TextureButton>
            ))}
          </div>
        </Step>
      </ol>

      <section aria-labelledby="cards-h" className="mt-8">
        <h2 id="cards-h" className="text-lg font-semibold text-ink-900">
          What the extension card says
        </h2>
        <p className="mt-1 max-w-prose text-ink-600">
          Each outcome shows a card like this on the AI site. Pick one to see its words.
        </p>
        <ExtensionTerminal
          tabs={OUTCOME_TABS}
          label="The card the extension shows for each of the five outcomes"
          className="mt-3"
        />
      </section>

      <ul className="mt-4 space-y-3" aria-label="Sample texts">
        {SAMPLES.map((s) => (
          <SampleCard key={`${s.id}-${lang}`} id={s.id} lang={lang} />
        ))}
      </ul>
    </main>
  );
}
