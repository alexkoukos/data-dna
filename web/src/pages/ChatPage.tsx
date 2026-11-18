import { useEffect, useRef, useState } from "react";
import {
  CheckIcon as Check,
  CopyIcon,
  RefreshCcwIcon,
  SendHorizontal,
  ShareIcon,
  ThumbsDownIcon,
  ThumbsUpIcon,
} from "lucide-react";
import { TextureButton } from "@/components/ui/texture-button";
import {
  ChatContainerContent,
  ChatContainerRoot,
  ChatContainerScrollAnchor,
} from "@/components/ui/chat-container";
import { FeedbackBar } from "@/components/ui/feedback-bar";
import { Loader } from "@/components/ui/loader";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageAvatar,
  MessageContent,
} from "@/components/ui/message";
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { PromptSuggestion } from "@/components/ui/prompt-suggestion";
import { ScrollButton } from "@/components/ui/scroll-button";
import { SystemMessage } from "@/components/ui/system-message";
import { ThinkingBar } from "@/components/ui/thinking-bar";
import { Bee } from "../components/Bee";
import { OutcomeChip, type Outcome } from "../components/OutcomeChip";
import { WarnCard } from "../components/WarnCard";
import { explainReason } from "../lib/explain";
import { ensureIdentity, sendChat, type ChatTurn, type Identity } from "../lib/chatApi";

/** Stock portrait for the person (Unsplash). If it cannot load, the initials show instead. */
const USER_AVATAR =
  "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=64&h=64&fit=crop&q=80";
/** The company AI's avatar is the Hive bee, drawn as an inline SVG so it works offline. */
const BEE_AVATAR =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="16" fill="#fffbeb"/><ellipse cx="16" cy="18" rx="8" ry="6" fill="#f59e0b"/><path d="M13 13v10M18 13v10" stroke="#262626" stroke-width="2" stroke-linecap="round"/><circle cx="24" cy="18" r="2.5" fill="#262626"/><ellipse cx="13" cy="11" rx="3.5" ry="2.5" fill="#fff" stroke="#262626" stroke-width="1"/><ellipse cx="19" cy="11" rx="3.5" ry="2.5" fill="#fff" stroke="#262626" stroke-width="1"/></svg>',
  );

const STARTERS = [
  "Summarise our data retention policy in two sentences",
  "Draft a polite reply declining a vendor's offer",
  "Explain what a masked value means in plain words",
];

interface Turn {
  id: number;
  from: "user" | "assistant";
  text: string;
  outcome?: Outcome;
  reasons?: string[];
  failed?: boolean;
}

interface Pending {
  text: string;
  reasons: string[];
  suggestion?: string;
}

function AnswerActions({
  text,
  onRetry,
  canRetry,
}: {
  text: string;
  onRetry: () => void;
  canRetry: boolean;
}) {
  const [vote, setVote] = useState<"up" | "down" | null>(null);
  const [done, setDone] = useState<"copy" | "share" | null>(null);
  const timer = useRef(0);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const flash = (what: "copy" | "share") => {
    setDone(what);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setDone(null), 1600);
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      flash("copy");
    } catch {
      /* the text stays selectable */
    }
  };
  const share = async () => {
    try {
      if (navigator.share) await navigator.share({ text });
      else {
        await navigator.clipboard.writeText(text);
        flash("share");
      }
    } catch {
      /* the person closed the share sheet */
    }
  };
  const ico = "size-4";

  return (
    <MessageActions className="-ml-2 gap-0.5">
      <MessageAction tooltip="Retry">
        <TextureButton
          variant="minimal"
          size="icon"
          aria-label="Retry"
          disabled={!canRetry}
          onClick={onRetry}
        >
          <RefreshCcwIcon className={ico} aria-hidden="true" />
        </TextureButton>
      </MessageAction>
      <MessageAction tooltip="Like">
        <TextureButton
          variant="minimal"
          size="icon"
          aria-label="Like"
          aria-pressed={vote === "up"}
          onClick={() => setVote(vote === "up" ? null : "up")}
        >
          <ThumbsUpIcon className={ico} aria-hidden="true" />
        </TextureButton>
      </MessageAction>
      <MessageAction tooltip="Dislike">
        <TextureButton
          variant="minimal"
          size="icon"
          aria-label="Dislike"
          aria-pressed={vote === "down"}
          onClick={() => setVote(vote === "down" ? null : "down")}
        >
          <ThumbsDownIcon className={ico} aria-hidden="true" />
        </TextureButton>
      </MessageAction>
      <MessageAction tooltip={done === "copy" ? "Copied" : "Copy"}>
        <TextureButton variant="minimal" size="icon" aria-label="Copy" onClick={copy}>
          {done === "copy" ? (
            <Check className={ico} aria-hidden="true" />
          ) : (
            <CopyIcon className={ico} aria-hidden="true" />
          )}
        </TextureButton>
      </MessageAction>
      <MessageAction tooltip={done === "share" ? "Copied to share" : "Share"}>
        <TextureButton variant="minimal" size="icon" aria-label="Share" onClick={share}>
          {done === "share" ? (
            <Check className={ico} aria-hidden="true" />
          ) : (
            <ShareIcon className={ico} aria-hidden="true" />
          )}
        </TextureButton>
      </MessageAction>
      <span className="sr-only" role="status">
        {done === "copy"
          ? "Answer copied"
          : done === "share"
            ? "Answer copied so you can share it"
            : ""}
      </span>
    </MessageActions>
  );
}

/** The company chat, built from the prompt-kit chat UI: ask the company's own AI. Risky messages are checked first. */
export default function ChatPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [rated, setRated] = useState<number | null>(null);
  const identity = useRef<Identity | null>(null);
  const next = useRef(1);

  const push = (t: Omit<Turn, "id">) => setTurns((all) => [...all, { ...t, id: next.current++ }]);

  /** Sends `text`, as a new turn or as a retry of the last one. */
  const send = async (text: string, opts: { ack?: string; retry?: boolean } = {}) => {
    const clean = text.trim();
    if (!clean || busy) return;
    setPending(null);
    setBusy(true);
    let history: ChatTurn[] = [];
    setTurns((all) => {
      const base = opts.retry
        ? all.slice(0, all.findLastIndex((t) => t.from === "user") + 1)
        : [...all, { id: next.current++, from: "user" as const, text: clean }];
      history = base.map((t) => ({ role: t.from, content: t.text }));
      return base;
    });
    if (!opts.retry) setDraft("");
    try {
      identity.current ??= await ensureIdentity();
      const res = await sendChat(identity.current, history, opts.ack);
      if (res.kind === "answer")
        push({ from: "assistant", text: res.text, outcome: res.outcome, reasons: res.reasons });
      else if (res.kind === "warn")
        setPending({ text: clean, reasons: res.reasons, suggestion: res.suggestion });
      else if (res.kind === "block")
        push({
          from: "assistant",
          text: `I did not send that. ${res.alternative}`,
          outcome: "block",
          reasons: res.reasons,
        });
      else push({ from: "assistant", text: res.message, failed: true });
    } catch {
      push({
        from: "assistant",
        text: "I could not reach the company AI. Check your connection and try again.",
        failed: true,
      });
    } finally {
      setBusy(false);
    }
  };

  const lastUser = [...turns].reverse().find((t) => t.from === "user");
  const lastAnswer = [...turns].reverse().find((t) => t.from === "assistant" && !t.failed);

  return (
    <main className="mx-auto flex h-[calc(100vh-4rem)] min-h-[32rem] max-w-3xl flex-col px-4 py-6">
      <header>
        <p className="eyebrow">Hive</p>
        <h1 className="text-2xl text-ink-900">Company AI</h1>
        <p className="mt-1 text-sm text-ink-600">
          Ask here instead of an outside AI tool. Messages are checked first, and answers come from
          the company&apos;s own model.
        </p>
      </header>

      <div className="relative mt-4 min-h-0 flex-1 rounded-lg border border-ink-200 bg-ink-50">
        <ChatContainerRoot className="h-full">
          <ChatContainerContent className="gap-6 p-4">
            {turns.length === 0 ? (
              <div className="flex flex-col items-center gap-4 py-8 text-center">
                <Bee size={72} />
                <p className="max-w-sm text-sm text-ink-600">
                  Nothing asked yet. Start with one of these, or type your own question below.
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {STARTERS.map((s) => (
                    <PromptSuggestion key={s} size="sm" onClick={() => void send(s)}>
                      {s}
                    </PromptSuggestion>
                  ))}
                </div>
              </div>
            ) : null}

            {turns.map((t, i) =>
              t.from === "user" ? (
                <Message key={t.id} className="justify-end">
                  <MessageContent className="max-w-[min(92%,36rem)] rounded-2xl rounded-tr-md bg-brand-600 p-3 text-ink-900">
                    {t.text}
                  </MessageContent>
                  <MessageAvatar src={USER_AVATAR} alt="You" fallback="You" />
                </Message>
              ) : (
                <Message key={t.id} className="items-start">
                  <MessageAvatar src={BEE_AVATAR} alt="Company AI" fallback="AI" />
                  <div className="flex min-w-0 max-w-[min(92%,40rem)] flex-col gap-2">
                    {t.failed ? (
                      <SystemMessage variant="error" fill>
                        {t.text}
                      </SystemMessage>
                    ) : (
                      <MessageContent
                        markdown
                        className="rounded-2xl rounded-tl-md border border-ink-200 bg-white p-3 text-ink-900"
                      >
                        {t.text}
                      </MessageContent>
                    )}
                    {!t.failed && t.outcome ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <OutcomeChip outcome={t.outcome} />
                        {t.reasons?.length ? (
                          <details className="text-sm text-ink-700">
                            <summary className="cursor-pointer py-2">Why?</summary>
                            <ul className="list-disc pl-5">
                              {t.reasons.map((r) => (
                                <li key={r}>{explainReason(r)}</li>
                              ))}
                            </ul>
                          </details>
                        ) : null}
                      </div>
                    ) : null}
                    {!t.failed ? (
                      <AnswerActions
                        text={t.text}
                        canRetry={!busy && i === turns.length - 1 && !!lastUser}
                        onRetry={() => lastUser && void send(lastUser.text, { retry: true })}
                      />
                    ) : null}
                    {!t.failed && lastAnswer?.id === t.id && !busy ? (
                      rated === t.id ? (
                        <p className="text-sm text-ink-600">Thanks. That helps me answer better.</p>
                      ) : (
                        <FeedbackBar
                          className="w-fit"
                          title="Was this response helpful?"
                          onHelpful={() => setRated(t.id)}
                          onNotHelpful={() => setRated(t.id)}
                          onClose={() => setRated(t.id)}
                        />
                      )
                    ) : null}
                  </div>
                </Message>
              ),
            )}

            {busy ? (
              <div className="flex items-center gap-3 text-sm text-ink-600" role="status">
                <Loader variant="dots" size="sm" />
                <ThinkingBar text="Thinking on the company server" />
              </div>
            ) : null}

            {pending ? (
              <WarnCard
                reasons={pending.reasons}
                suggestion={pending.suggestion}
                busy={busy}
                onUseSuggestion={
                  pending.suggestion ? () => void send(pending.suggestion ?? "") : undefined
                }
                onEdit={() => {
                  setDraft(pending.text);
                  setPending(null);
                }}
                onSendAnyway={(reason) => void send(pending.text, { ack: reason })}
                onCancel={() => setPending(null)}
              />
            ) : null}
            <ChatContainerScrollAnchor />
          </ChatContainerContent>
          <div className="absolute bottom-3 right-3">
            <ScrollButton aria-label="Scroll to the newest message" />
          </div>
        </ChatContainerRoot>
      </div>

      <PromptInput
        className="mt-4 rounded-2xl border border-ink-300 bg-white p-2"
        value={draft}
        onValueChange={setDraft}
        isLoading={busy}
        onSubmit={() => void send(draft)}
      >
        <PromptInputTextarea aria-label="Your question" placeholder="Ask the company AI" />
        <PromptInputActions className="justify-end pt-2">
          <PromptInputAction tooltip="Send (Enter)">
            <TextureButton
              variant="primary"
              aria-label="Send"
              disabled={busy || !draft.trim()}
              onClick={() => void send(draft)}
            >
              <SendHorizontal className="size-4" aria-hidden="true" />
              Ask company AI
            </TextureButton>
          </PromptInputAction>
        </PromptInputActions>
      </PromptInput>
    </main>
  );
}
