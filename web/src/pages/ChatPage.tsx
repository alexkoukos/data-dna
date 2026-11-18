import { useEffect, useRef, useState } from "react";
import {
  BrainIcon,
  CheckIcon as Check,
  CopyIcon,
  PanelLeft,
  Pencil,
  RefreshCcwIcon,
  ShareIcon,
  ThumbsDownIcon,
  ThumbsUpIcon,
  Trash,
} from "lucide-react";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { PromptBox } from "../components/chat/PromptBox";
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
import { PromptSuggestion } from "@/components/ui/prompt-suggestion";
import { ScrollButton } from "@/components/ui/scroll-button";
import { SystemMessage } from "@/components/ui/system-message";
import { TextureButton } from "@/components/ui/texture-button";
import { ThinkingBar } from "@/components/ui/thinking-bar";
import { Tool } from "@/components/ui/tool";
import { cn } from "@/lib/utils";
import { Bee } from "../components/Bee";
import { OutcomeChip } from "../components/OutcomeChip";
import { WarnCard } from "../components/WarnCard";
import {
  ensureIdentity,
  sendChat,
  takeHandoff,
  type ChatAttachment,
  type ChatTurn,
  type Identity,
} from "../lib/chatApi";
import { PROMPT_GROUPS } from "../lib/chatPrompts";
import {
  loadChats,
  newChat,
  saveChats,
  titleFrom,
  type Chat,
  type StoredTurn,
} from "../lib/chatStore";
import { explainReason } from "../lib/explain";

/** The person's profile picture, served with the app. If it cannot load, the initials show instead. */
const USER_AVATAR = "/brand/avatar-user.jpg";
/** The company AI's avatar is the Hive bee, drawn inline so it works offline. */
const BEE_AVATAR =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="16" fill="#fffbeb"/><ellipse cx="16" cy="18" rx="8" ry="6" fill="#f59e0b"/><path d="M13 13v10M18 13v10" stroke="#262626" stroke-width="2" stroke-linecap="round"/><circle cx="24" cy="18" r="2.5" fill="#262626"/><ellipse cx="13" cy="11" rx="3.5" ry="2.5" fill="#fff" stroke="#262626" stroke-width="1"/><ellipse cx="19" cy="11" rx="3.5" ry="2.5" fill="#fff" stroke="#262626" stroke-width="1"/></svg>',
  );

interface Pending {
  text: string;
  reasons: string[];
  suggestion?: string;
}

const ico = "size-4";
const iconBtn = "rounded-full";

function ActionButton({
  label,
  onClick,
  disabled,
  pressed,
  children,
}: {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  pressed?: boolean;
  children: React.ReactNode;
}) {
  return (
    <MessageAction tooltip={label} delayDuration={100}>
      <TextureButton
        variant="minimal"
        size="icon"
        className={iconBtn}
        aria-label={label}
        aria-pressed={pressed}
        disabled={disabled}
        onClick={onClick}
      >
        {children}
      </TextureButton>
    </MessageAction>
  );
}

function AnswerActions({
  text,
  onRetry,
  canRetry,
  last,
}: {
  text: string;
  onRetry: () => void;
  canRetry: boolean;
  last: boolean;
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
  return (
    <MessageActions
      className={cn(
        "-ml-2.5 flex gap-0 opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100",
        last && "opacity-100",
      )}
    >
      <ActionButton label="Retry" onClick={onRetry} disabled={!canRetry}>
        <RefreshCcwIcon className={ico} aria-hidden="true" />
      </ActionButton>
      <ActionButton
        label="Like"
        pressed={vote === "up"}
        onClick={() => setVote(vote === "up" ? null : "up")}
      >
        <ThumbsUpIcon className={ico} aria-hidden="true" />
      </ActionButton>
      <ActionButton
        label="Dislike"
        pressed={vote === "down"}
        onClick={() => setVote(vote === "down" ? null : "down")}
      >
        <ThumbsDownIcon className={ico} aria-hidden="true" />
      </ActionButton>
      <ActionButton label={done === "copy" ? "Copied" : "Copy"} onClick={copy}>
        {done === "copy" ? (
          <Check className={ico} aria-hidden="true" />
        ) : (
          <CopyIcon className={ico} aria-hidden="true" />
        )}
      </ActionButton>
      <ActionButton label={done === "share" ? "Copied to share" : "Share"} onClick={share}>
        {done === "share" ? (
          <Check className={ico} aria-hidden="true" />
        ) : (
          <ShareIcon className={ico} aria-hidden="true" />
        )}
      </ActionButton>
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

/** The company chat, built from the prompt-kit chat UI: history sidebar, conversation, prompt input. */
export default function ChatPage() {
  const [chats, setChats] = useState<Chat[]>(loadChats);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [handoffNote, setHandoffNote] = useState("");
  const [pending, setPending] = useState<Pending | null>(null);
  const [rated, setRated] = useState<number | null>(null);
  const [category, setCategory] = useState("");
  const [sidebar, setSidebar] = useState(
    () => typeof matchMedia === "function" && matchMedia("(min-width: 768px)").matches,
  );
  const identity = useRef<Identity | null>(null);
  const chatsRef = useRef(chats);
  chatsRef.current = chats;
  const counter = useRef(0);

  useEffect(() => saveChats(chats), [chats]);

  // Hive stopped a message or a file in the browser and passed it here: it arrives in the box.
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("handoff");
    if (!id) return;
    window.history.replaceState(null, "", window.location.pathname);
    void takeHandoff(id).then((h) => {
      if (!h) {
        setHandoffNote("That hand-off has expired. Paste or add it again.");
        return;
      }
      setDraft(h.text || (h.attachments.length ? "Summarise this file." : ""));
      setAttachments(h.attachments);
      setHandoffNote(
        "Moved here from the browser. This chat stays inside the company. Press Send when you are ready.",
      );
    });
  }, []);

  const active = chats.find((c) => c.id === activeId) ?? null;
  const turns = active?.turns ?? [];
  const makeId = () => Date.now() * 100 + (counter.current++ % 100);
  const turnsOf = (id: string) => chatsRef.current.find((c) => c.id === id)?.turns ?? [];

  const update = (id: string, change: (c: Chat) => Partial<Chat>) =>
    setChats((all) =>
      all.map((c) => (c.id === id ? { ...c, ...change(c), updated: Date.now() } : c)),
    );
  const append = (id: string, t: Omit<StoredTurn, "id">) =>
    update(id, (c) => ({ turns: [...c.turns, { ...t, id: makeId() }] }));

  /** Sends `text` as a new turn, or retries the last question when `retry` is set. */
  const send = async (text: string, opts: { ack?: string; retry?: boolean } = {}) => {
    const clean = text.trim() || (attachments.length ? "Summarise this file." : "");
    if (!clean || busy) return;
    const files = opts.retry ? [] : attachments;
    const shown = files.length
      ? `${clean}\n\n📎 ${files.map((f) => f.filename).join(", ")}`
      : clean;
    let id = activeId;
    if (!id) {
      const c = newChat();
      id = c.id;
      setChats((all) => [c, ...all]);
      setActiveId(id);
    }
    setPending(null);
    setBusy(true);
    const before = id === activeId ? turnsOf(id) : [];
    const base: StoredTurn[] = opts.retry
      ? before.slice(0, before.findLastIndex((t) => t.from === "user") + 1)
      : [...before, { id: makeId(), from: "user", text: shown }];
    const first = before.length === 0;
    update(id, (c) => ({ turns: base, title: first && !opts.retry ? titleFrom(clean) : c.title }));
    if (!opts.retry) {
      setDraft("");
      setAttachments([]);
      setHandoffNote("");
    }
    const history: ChatTurn[] = base.map((t) => ({ role: t.from, content: t.text }));
    if (files.length) history[history.length - 1].content = clean;
    try {
      identity.current ??= await ensureIdentity();
      const res = await sendChat(identity.current, history, opts.ack, files);
      if (res.kind === "answer")
        append(id, {
          from: "assistant",
          text: res.text,
          outcome: res.outcome,
          reasons: res.reasons,
        });
      else if (res.kind === "warn")
        setPending({ text: clean, reasons: res.reasons, suggestion: res.suggestion });
      else if (res.kind === "block")
        append(id, {
          from: "assistant",
          text: `I did not send that. ${res.alternative}`,
          outcome: "block",
          reasons: res.reasons,
        });
      else append(id, { from: "assistant", text: res.message, failed: true });
    } catch {
      append(id, {
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
  const empty = turns.length === 0 && !pending && !busy;
  const group = PROMPT_GROUPS.find((g) => g.label === category);
  const closeOnMobile = () => matchMedia("(max-width: 767px)").matches && setSidebar(false);

  const removeTurn = (t: StoredTurn) => {
    if (!active) return;
    const i = active.turns.findIndex((x) => x.id === t.id);
    const next = active.turns[i + 1];
    const drop = new Set([t.id, ...(next?.from === "assistant" ? [next.id] : [])]);
    update(active.id, (c) => ({ turns: c.turns.filter((x) => !drop.has(x.id)) }));
  };
  const editTurn = (t: StoredTurn) => {
    if (!active) return;
    const i = active.turns.findIndex((x) => x.id === t.id);
    update(active.id, (c) => ({ turns: c.turns.slice(0, i) }));
    setDraft(t.text);
  };

  return (
    <div className="flex h-[calc(100dvh-61px)] min-h-[32rem] overflow-hidden bg-white">
      <ChatSidebar
        chats={chats}
        activeId={activeId}
        open={sidebar}
        onSelect={(id) => {
          setActiveId(id);
          setPending(null);
          closeOnMobile();
        }}
        onNew={() => {
          setActiveId(null);
          setDraft("");
          setPending(null);
          closeOnMobile();
        }}
        onRename={(id, title) => update(id, () => ({ title }))}
        onDelete={(id) => {
          setChats((all) => all.filter((c) => c.id !== id));
          if (id === activeId) setActiveId(null);
        }}
        onClose={() => setSidebar(false)}
      />

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="z-10 flex h-14 w-full shrink-0 items-center gap-2 border-b border-ink-200 bg-white px-4">
          <TextureButton
            variant="minimal"
            size="icon"
            aria-label={sidebar ? "Hide chat history" : "Show chat history"}
            aria-expanded={sidebar}
            onClick={() => setSidebar((s) => !s)}
          >
            <PanelLeft className="size-4" aria-hidden="true" />
          </TextureButton>
          <h1 className="min-w-0 truncate text-lg text-ink-900">{active?.title ?? "Company AI"}</h1>
          <span className="ml-auto hidden shrink-0 text-xs text-ink-600 sm:inline">
            Messages are checked first. Answers come from the company&apos;s own model.
          </span>
        </header>

        {empty ? (
          <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-4 pb-10">
            <div className="w-full max-w-3xl">
              <div className="mb-6 flex flex-col items-center gap-3 text-center">
                <Bee size={72} />
                <h2 className="text-3xl text-ink-900">What can I help with?</h2>
              </div>
              <PromptBox
                value={draft}
                onChange={setDraft}
                onSend={() => void send(draft)}
                busy={busy}
                attachments={attachments}
                onAttachmentsChange={setAttachments}
              />
              {handoffNote ? (
                <p role="status" className="mt-2 px-2 text-sm text-ink-700">
                  {handoffNote}
                </p>
              ) : null}
              <div className="mt-4 min-h-24">
                {group ? (
                  <div className="flex w-full flex-col space-y-1">
                    {group.items.map((s) => (
                      <PromptSuggestion
                        key={s}
                        highlight={group.highlight}
                        className="flex h-auto flex-wrap text-left"
                        onClick={() => setDraft(s)}
                      >
                        {s}
                      </PromptSuggestion>
                    ))}
                  </div>
                ) : (
                  <div className="flex w-full flex-wrap items-stretch justify-center gap-2">
                    {PROMPT_GROUPS.map((g) => (
                      <PromptSuggestion key={g.label} onClick={() => setCategory(g.label)}>
                        <BrainIcon className="mr-2 size-4" aria-hidden="true" />
                        {g.label}
                      </PromptSuggestion>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="relative min-h-0 flex-1">
              <ChatContainerRoot className="h-full">
                <ChatContainerContent className="space-y-6 px-2 py-8 sm:px-5">
                  {turns.map((t, i) => {
                    const last = i === turns.length - 1;
                    if (t.from === "user")
                      return (
                        <Message
                          key={t.id}
                          className="mx-auto flex w-full max-w-3xl items-start justify-end gap-3 px-2"
                        >
                          <div className="group flex min-w-0 flex-col items-end gap-1">
                            <MessageContent className="max-w-[85%] whitespace-pre-wrap rounded-3xl bg-brand-100 px-5 py-2.5 text-ink-900 sm:max-w-[75%]">
                              {t.text}
                            </MessageContent>
                            <MessageActions className="flex gap-0 opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100">
                              <ActionButton
                                label="Edit"
                                onClick={() => editTurn(t)}
                                disabled={busy}
                              >
                                <Pencil className={ico} aria-hidden="true" />
                              </ActionButton>
                              <ActionButton
                                label="Delete"
                                onClick={() => removeTurn(t)}
                                disabled={busy}
                              >
                                <Trash className={ico} aria-hidden="true" />
                              </ActionButton>
                              <ActionButton
                                label="Copy"
                                onClick={() => void navigator.clipboard?.writeText(t.text)}
                              >
                                <CopyIcon className={ico} aria-hidden="true" />
                              </ActionButton>
                            </MessageActions>
                          </div>
                          <MessageAvatar src={USER_AVATAR} alt="You" fallback="You" />
                        </Message>
                      );
                    const asked = turns[i - 1];
                    return (
                      <Message
                        key={t.id}
                        className="mx-auto flex w-full max-w-3xl items-start gap-3 px-2"
                      >
                        <MessageAvatar src={BEE_AVATAR} alt="Company AI" fallback="AI" />
                        <div className="group flex min-w-0 flex-1 flex-col gap-2">
                          {t.failed ? (
                            <SystemMessage variant="error" fill>
                              {t.text}
                            </SystemMessage>
                          ) : (
                            <MessageContent
                              markdown
                              className="flex-1 rounded-lg bg-transparent p-0 text-ink-900 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-5"
                            >
                              {t.text}
                            </MessageContent>
                          )}
                          {!t.failed && t.outcome ? (
                            <div className="flex flex-col items-start gap-2">
                              <OutcomeChip outcome={t.outcome} />
                              {t.reasons?.length ? (
                                <Tool
                                  className="w-full max-w-md"
                                  toolPart={{
                                    type: "hive_check",
                                    state: "output-available",
                                    input: { message: `${asked?.text.length ?? 0} characters` },
                                    output: {
                                      decision: t.outcome,
                                      why: t.reasons.map(explainReason).join("; "),
                                    },
                                  }}
                                />
                              ) : null}
                            </div>
                          ) : null}
                          {!t.failed ? (
                            <AnswerActions
                              text={t.text}
                              last={last}
                              canRetry={!busy && last && !!lastUser}
                              onRetry={() => lastUser && void send(lastUser.text, { retry: true })}
                            />
                          ) : null}
                          {!t.failed && lastAnswer?.id === t.id && !busy ? (
                            rated === t.id ? (
                              <p className="text-sm text-ink-600">
                                Thanks. That helps me answer better.
                              </p>
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
                    );
                  })}

                  {busy ? (
                    <div
                      className="mx-auto flex w-full max-w-3xl items-center gap-3 px-2 text-sm text-ink-600"
                      role="status"
                    >
                      <Loader variant="dots" size="sm" />
                      <ThinkingBar text="Thinking on the company server" />
                    </div>
                  ) : null}

                  {pending ? (
                    <div className="mx-auto w-full max-w-3xl px-2">
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
                    </div>
                  ) : null}
                  <ChatContainerScrollAnchor />
                </ChatContainerContent>
                <div className="absolute bottom-4 left-1/2 flex w-full max-w-3xl -translate-x-1/2 justify-end px-5">
                  <ScrollButton aria-label="Scroll to the newest message" className="shadow-sm" />
                </div>
              </ChatContainerRoot>
            </div>
            <div className="z-10 shrink-0 bg-white px-3 pb-3 md:px-5 md:pb-5">
              <div className="mx-auto max-w-3xl">
                <PromptBox
                  value={draft}
                  onChange={setDraft}
                  onSend={() => void send(draft)}
                  busy={busy}
                  attachments={attachments}
                  onAttachmentsChange={setAttachments}
                />
                {handoffNote ? (
                  <p role="status" className="mt-2 px-2 text-sm text-ink-700">
                    {handoffNote}
                  </p>
                ) : null}
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
