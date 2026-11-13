import { useCallback, useEffect, useRef, useState } from "react";
import { ChatSkeleton } from "../components/ChatSkeleton";
import { Composer } from "../components/Composer";
import { MessageBubble, type ChatMessage } from "../components/MessageBubble";
import { StarterPrompts } from "../components/StarterPrompts";
import { WarnCard } from "../components/WarnCard";
import { ensureIdentity, sendChat, type ChatTurn, type Identity } from "../lib/chatApi";

type Setup = { status: "loading" } | { status: "ready"; identity: Identity } | { status: "failed" };

let counter = 0;
const nextId = () => `m${++counter}`;

/** Container: owns the conversation, the personal key and every call to the gateway. */
export default function ChatPage() {
  const [setup, setSetup] = useState<Setup>({ status: "loading" });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [held, setHeld] = useState<{ id: string; text: string; reasons: string[] } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const connect = useCallback(() => {
    ensureIdentity().then(
      (identity) => setSetup({ status: "ready", identity }),
      () => setSetup({ status: "failed" }),
    );
  }, []);
  const retry = () => {
    setSetup({ status: "loading" });
    connect();
  };

  useEffect(() => {
    connect();
  }, [connect]);
  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages, held, busy]);

  /** Earlier turns that passed untouched. Turns that were masked or held are not sent again. */
  const cleanHistory = (): ChatTurn[] => {
    const turns: ChatTurn[] = [];
    for (let i = 0; i + 1 < messages.length; i += 2) {
      const [q, a] = [messages[i], messages[i + 1]];
      if (q?.role === "user" && a?.role === "assistant" && q.outcome === undefined) {
        turns.push({ role: "user", content: q.text }, { role: "assistant", content: a.text });
      }
    }
    return turns;
  };

  const deliver = async (text: string, userId: string, ack?: string) => {
    if (setup.status !== "ready") return;
    setBusy(true);
    setError(null);
    const result = await sendChat(
      setup.identity,
      [...cleanHistory(), { role: "user", content: text }],
      ack,
    );
    setBusy(false);

    if (result.kind === "warn") {
      setMessages((m) =>
        m.map((x) => (x.id === userId ? { ...x, outcome: "warn", reasons: result.reasons } : x)),
      );
      setHeld({ id: userId, text, reasons: result.reasons });
      return;
    }
    if (result.kind === "block") {
      setHeld(null);
      setMessages((m) =>
        m.map((x) =>
          x.id === userId
            ? { ...x, outcome: "block", reasons: result.reasons, alternative: result.alternative }
            : x,
        ),
      );
      return;
    }
    if (result.kind === "error") {
      setHeld(null);
      setMessages((m) => m.filter((x) => x.id !== userId));
      setDraft(text);
      setError(result.message);
      return;
    }
    setHeld(null);
    setMessages((m) => [
      ...m.map((x) =>
        x.id === userId && result.outcome !== "allow"
          ? { ...x, outcome: result.outcome, reasons: result.reasons }
          : x,
      ),
      {
        id: nextId(),
        role: "assistant",
        text: result.text,
        outcome: result.outcome === "local" ? "local" : "allow",
      },
    ]);
  };

  const send = () => {
    const text = draft.trim();
    if (!text || busy) return;
    const id = nextId();
    setMessages((m) => [...m, { id, role: "user", text }]);
    setDraft("");
    void deliver(text, id);
  };

  const sendAnyway = (reason: string) => {
    if (!held) return;
    void deliver(held.text, held.id, reason);
  };

  const editHeld = () => {
    if (!held) return;
    setDraft(held.text);
    setMessages((m) => m.filter((x) => x.id !== held.id));
    setHeld(null);
  };

  const cancelHeld = () => {
    if (!held) return;
    setMessages((m) => m.filter((x) => x.id !== held.id));
    setHeld(null);
  };

  return (
    <main className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-3xl flex-col px-4 py-6">
      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-ink-900">Company Chat</h1>
        <p className="mt-1 text-ink-600">
          Your questions stay inside. We check each message first.
        </p>
      </header>

      {setup.status === "loading" ? <ChatSkeleton /> : null}

      {setup.status === "failed" ? (
        <div
          role="alert"
          className="rounded-2xl border border-block-fg/30 bg-block-bg p-4 text-block-fg"
        >
          <p className="font-semibold">We could not start your chat.</p>
          <p className="mt-1 text-sm">The server did not answer. Try again in a moment.</p>
          <button
            type="button"
            onClick={retry}
            className="mt-3 min-h-11 rounded-lg bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Try again
          </button>
        </div>
      ) : null}

      {setup.status === "ready" ? (
        <>
          <div className="flex-1">
            {messages.length === 0 ? (
              <StarterPrompts onPick={setDraft} />
            ) : (
              <div role="log" aria-label="Conversation" aria-live="polite">
                <ol className="space-y-4">
                  {messages.map((m) => (
                    <MessageBubble key={m.id} message={m} />
                  ))}
                </ol>
              </div>
            )}
            {busy ? (
              <p role="status" className="mt-4 text-sm text-ink-600">
                Checking and answering…
              </p>
            ) : null}
            {held ? (
              <div className="mt-4">
                <WarnCard
                  reasons={held.reasons}
                  busy={busy}
                  onEdit={editHeld}
                  onSendAnyway={sendAnyway}
                  onCancel={cancelHeld}
                />
              </div>
            ) : null}
            {error ? (
              <p role="alert" className="mt-4 rounded-xl bg-block-bg p-3 text-sm text-block-fg">
                {error} Your message is back in the box.
              </p>
            ) : null}
            <div ref={endRef} />
          </div>
          {held === null ? (
            <div className="sticky bottom-0 mt-6 bg-ink-50 pb-2 pt-2">
              <Composer value={draft} onChange={setDraft} onSend={send} disabled={busy} />
            </div>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
