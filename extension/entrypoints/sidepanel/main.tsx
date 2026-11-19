import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/poppins/400.css";
import "@fontsource/poppins/700.css";
import "@fontsource/poppins/600.css";
import "@fontsource/space-grotesk/600.css";
import "../../src/ui.css";
import { ExternalLink, House, SendHorizontal, X } from "lucide-react";
import { TextureStyles } from "../../src/TextureStyles";
import {
  AnswerActions,
  Avatar,
  Conversation,
  ConversationContent,
  Message,
  MessageContent,
} from "../../src/chat";

const STARTERS = [
  "Summarise this report",
  "Draft a reply to a customer",
  "Explain this contract clause",
];

interface Turn {
  role: "me" | "ai";
  text: string;
  ready?: boolean;
}

/** The same chat also opens as a full tab (?tab=1), for long answers or a second screen. */
const IN_TAB = new URLSearchParams(location.search).has("tab");
const openTab = () =>
  void chrome.tabs.create({ url: chrome.runtime.getURL("sidepanel.html?tab=1") });

function Panel() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  const ask = async (prompt: string) => {
    if (!prompt.trim()) return;
    setTurns((t) => [...t, { role: "me", text: prompt }]);
    setDraft("");
    setBusy(true);
    const res = await chrome.runtime.sendMessage({ type: "askLocal", prompt });
    setTurns((t) => [
      ...t,
      res?.answer
        ? { role: "ai", text: res.answer, ready: res.ready }
        : {
            role: "ai",
            text: "The company AI could not be reached. Check the server address in Settings, then try again.",
            ready: false,
          },
    ]);
    setBusy(false);
  };

  useEffect(() => {
    // A prompt handed over from the card on an AI site ("Ask the company AI").
    const take = async () => {
      const { pendingPrompt } = await chrome.storage.session.get("pendingPrompt");
      if (typeof pendingPrompt === "string" && pendingPrompt) {
        await chrome.storage.session.remove("pendingPrompt");
        setDraft(pendingPrompt);
      }
    };
    void take();
    const onChange = (c: Record<string, chrome.storage.StorageChange>, area: string) => {
      if (area === "session" && c.pendingPrompt?.newValue) void take();
    };
    chrome.storage.onChanged.addListener(onChange);
    return () => chrome.storage.onChanged.removeListener(onChange);
  }, []);

  useEffect(() => {
    if (IN_TAB) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") window.close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    // Braces matter: an effect must not return the value of scrollIntoView (a Promise in new Chrome).
    end.current?.scrollIntoView({ block: "end" });
  }, [turns, busy]);

  return (
    <>
      <TextureStyles />
      <div
        className={`wrap${IN_TAB ? " in-tab" : ""}`}
        style={{ display: "flex", flexDirection: "column", height: "100vh" }}
      >
        <header className="sp-top">
          <picture>
            <source media="(prefers-color-scheme: dark)" srcSet="/brand/sentry-wordmark-dark.svg" />
            <img className="wordmark" src="/brand/sentry-wordmark.svg" alt="Sentry" width={120} />
          </picture>
          {!IN_TAB && (
            <div className="sp-tools">
              <button type="button" className="sp-tool" onClick={openTab}>
                <ExternalLink size={14} aria-hidden="true" />
                Open in a tab
              </button>
              <button
                type="button"
                className="sp-tool"
                onClick={() => window.close()}
                aria-label="Close Company AI"
              >
                <X size={14} aria-hidden="true" />
                Close
              </button>
            </div>
          )}
        </header>
        <div className="sp-title">
          <h1>Company AI</h1>
          <span className="badge">
            <House size={12} aria-hidden="true" />
            Stays inside the company
          </span>
        </div>
        <div className="chat-scroll">
          <Conversation>
            <ConversationContent>
              {turns.length === 0 && (
                <div className="sp-empty">
                  <p className="muted">
                    Ask here instead of an outside AI tool. Your text is answered by the
                    company&apos;s own model and never leaves the company.
                  </p>
                  <div className="sp-starters" role="group" aria-label="Ideas to start with">
                    {STARTERS.map((q) => (
                      <button
                        key={q}
                        type="button"
                        className="sp-starter"
                        onClick={() => {
                          setDraft(q);
                          input.current?.focus();
                        }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {turns.map((t, i) => {
                const from = t.role === "me" ? "user" : "assistant";
                const lastAsk = [...turns.slice(0, i)].reverse().find((x) => x.role === "me");
                return (
                  <Message key={i} from={from}>
                    <Avatar from={from} />
                    <MessageContent>{t.text}</MessageContent>
                    {from === "assistant" && (
                      <>
                        <p className="msg-note">
                          {t.ready
                            ? "Answered locally"
                            : "Stand-in answer (local model not running)"}
                        </p>
                        <AnswerActions
                          text={t.text}
                          canRetry={!!lastAsk && !busy}
                          onRetry={() => lastAsk && void ask(lastAsk.text)}
                        />
                      </>
                    )}
                  </Message>
                );
              })}
              {busy && <p className="muted">Thinking, on the company server…</p>}
              <div ref={end} />
            </ConversationContent>
          </Conversation>
        </div>
        <form
          className="sp-composer"
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy) void ask(draft);
          }}
        >
          <label htmlFor="q" className="sr-only">
            Your question
          </label>
          <textarea
            id="q"
            ref={input}
            rows={2}
            value={draft}
            placeholder="Ask anything, for example: summarise this report"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              // Enter sends; Shift+Enter adds a line. Never send while an input method is composing.
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                if (!busy && draft.trim()) void ask(draft);
              }
            }}
          />
          <div className="sp-composer-row">
            <span className="muted sp-hint">
              <kbd>Enter</kbd> to send, <kbd>Shift</kbd> + <kbd>Enter</kbd> for a new line
            </span>
            <button
              className="primary"
              type="submit"
              aria-label="Ask company AI"
              disabled={busy || !draft.trim()}
            >
              <SendHorizontal size={16} aria-hidden="true" />
              Ask
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

document.body.classList.add("fit");
createRoot(document.getElementById("root")!).render(<Panel />);
