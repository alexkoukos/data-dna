import { useEffect, useState } from "react";
import { CopyField } from "../components/CopyField";
import { CheckIcon } from "../components/icons";
import { ErrorPanel, Skeleton } from "../components/ui";
import { ensureIdentity, type Identity } from "../lib/chatApi";
import { buildSnippets, gatewayUrl } from "../lib/snippets";
import { useFetch } from "../lib/useFetch";

const POLL_MS = 3000;

/** "Waiting for first request" until the gateway has checked something for this key's user. */
function LiveStatus({ userId }: { userId: string }) {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    if (seen) return;
    let stop = false;
    async function poll() {
      try {
        const res = await fetch(`/api/v1/users/${encodeURIComponent(userId)}/seen`);
        if (res.ok && ((await res.json()) as { seen: boolean }).seen && !stop) setSeen(true);
      } catch {
        // The next poll tries again.
      }
    }
    void poll();
    const id = window.setInterval(poll, POLL_MS);
    return () => {
      stop = true;
      window.clearInterval(id);
    };
  }, [seen, userId]);

  return (
    <p
      role="status"
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold ${seen ? "bg-allow-bg text-allow-fg" : "bg-ink-100 text-ink-700"}`}
    >
      {seen ? (
        <>
          <CheckIcon /> Connected. The gateway has checked a request with this key.
        </>
      ) : (
        <>
          <span
            aria-hidden="true"
            className="h-2 w-2 animate-pulse rounded-full bg-ink-500 motion-reduce:animate-none"
          />
          Waiting for first request. Run one of the snippets below.
        </>
      )}
    </p>
  );
}

function Snippets({ identity, url }: { identity: Identity; url: string }) {
  const snippets = buildSnippets(url, identity.key, identity.model);
  const [active, setActive] = useState(snippets[0].id);
  const current = snippets.find((s) => s.id === active) ?? snippets[0];
  const [copied, setCopied] = useState(false);

  async function copy() {
    if (!current.code) return;
    try {
      await navigator.clipboard.writeText(current.code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // The code is on screen, so it can still be selected by hand.
    }
  }

  return (
    <section aria-labelledby="snippets-h" className="mt-8">
      <h2 id="snippets-h" className="text-lg font-semibold text-ink-900">
        Connect your tool
      </h2>
      <div role="tablist" aria-label="Ways to connect" className="mt-3 flex flex-wrap gap-2">
        {snippets.map((s) => (
          <button
            key={s.id}
            role="tab"
            type="button"
            id={`tab-${s.id}`}
            aria-selected={s.id === active}
            aria-controls="snippet-panel"
            onClick={() => setActive(s.id)}
            className={`min-h-11 rounded-lg px-3 text-sm font-medium ${s.id === active ? "bg-brand-50 text-brand-700" : "text-ink-600 hover:bg-ink-100"}`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        id="snippet-panel"
        aria-labelledby={`tab-${current.id}`}
        className="mt-3 rounded-2xl border border-ink-200 bg-white p-4"
      >
        <p className="text-ink-700">{current.note}</p>
        {current.code && (
          <>
            <pre
              tabIndex={0}
              aria-label={`${current.label} code`}
              className="mt-3 overflow-x-auto rounded-lg bg-ink-900 p-4 text-sm text-ink-50"
            >
              <code>{current.code}</code>
            </pre>
            <button
              type="button"
              onClick={copy}
              className="mt-3 min-h-11 rounded-lg bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700"
            >
              {copied ? "Copied" : "Copy this code"}
            </button>
          </>
        )}
      </div>
    </section>
  );
}

export default function ConnectPage() {
  const [state, reload] = useFetch(ensureIdentity);
  const url = gatewayUrl(window.location);

  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-2xl font-semibold text-ink-900">Connect a tool</h1>
      <p className="mt-1 max-w-prose text-ink-600">
        Point any tool that speaks the OpenAI format at the address below, with your personal key.
        Every request is then checked before it leaves the company.
      </p>

      {state.status === "loading" && (
        <div role="status" aria-label="Loading your connection details" className="mt-6 space-y-3">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
          <Skeleton className="h-40" />
        </div>
      )}
      {state.status === "error" && (
        <div className="mt-6">
          <ErrorPanel what="your connection details" onRetry={reload} />
        </div>
      )}
      {state.status === "ready" && (
        <>
          <div className="mt-6 space-y-4">
            <CopyField label="Gateway address" value={url} />
            <CopyField label="Personal key" value={state.data.key} secret />
            <p className="text-sm text-ink-600">
              This key is yours. Do not share it. The company chat uses the same key.
            </p>
          </div>
          <div className="mt-6">
            <LiveStatus userId={state.data.userId} />
          </div>
          <Snippets identity={state.data} url={url} />
        </>
      )}
    </main>
  );
}
