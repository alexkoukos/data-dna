import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/poppins/400.css";
import "@fontsource/poppins/700.css";
import "@fontsource/poppins/600.css";
import "@fontsource/playfair-display/600.css";
import "../../src/ui.css";
import { ExternalLink, House, SendHorizontal } from "lucide-react";
import { TextureStyles } from "../../src/TextureStyles";
import {
  AnswerActions,
  Avatar,
  Conversation,
  ConversationContent,
  Message,
  MessageContent,
} from "../../src/chat";

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
        <picture>
          <source media="(prefers-color-scheme: dark)" srcSet="/brand/hive-wordmark-dark.svg" />
          <img className="wordmark" src="/brand/hive-wordmark.svg" alt="Hive" width={120} />
        </picture>
        <div
          className="row"
          style={{ justifyContent: "space-between", marginTop: 12, flexWrap: "wrap" }}
        >
          <h1>Company AI</h1>
          <span className="badge">
            <House size={12} aria-hidden="true" />
            Stays inside the company
          </span>
          {!IN_TAB && (
            <button
              type="button"
              onClick={openTab}
              style={{ minHeight: 36, padding: "0 12px", fontSize: 13 }}
            >
              <ExternalLink size={14} aria-hidden="true" />
              Open in a tab
            </button>
          )}
        </div>
        <div className="chat-scroll">
          <Conversation>
            <ConversationContent>
              {turns.length === 0 && (
                <p className="muted">
                  Ask here instead of an outside AI tool. Your text is answered by the
                  company&apos;s own model and never leaves the company.
                </p>
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
          onSubmit={(e) => {
            e.preventDefault();
            void ask(draft);
          }}
        >
          <label htmlFor="q">Your question</label>
          <textarea id="q" value={draft} onChange={(e) => setDraft(e.target.value)} />
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 8 }}>
            <button className="primary" type="submit" disabled={busy || !draft.trim()}>
              <SendHorizontal size={16} aria-hidden="true" />
              Ask company AI
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<Panel />);
