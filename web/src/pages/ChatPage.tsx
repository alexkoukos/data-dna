import { useEffect, useRef, useState } from "react";
import {
  BrainIcon,
  FileText,
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
import { UploadBanner } from "../components/chat/UploadBanner";
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
import { Sentinel } from "../components/Sentinel";
import { RequestToolForm } from "../components/RequestToolForm";
import { OutcomeChip } from "../components/OutcomeChip";
import { WarnCard } from "../components/WarnCard";
import {
  composeMessage,
  DEFAULT_LIMITS,
  fileSummary,
  precheck,
  toSent,
  uploadHint,
  type Attachment,
  type ReadFile,
} from "../lib/attachments";
import { ensureIdentity, sendChat, type ChatTurn, type Identity } from "../lib/chatApi";
import { extractFile, fetchFileLimits } from "../lib/filesApi";
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
import { collectOutcomes, outcomeText } from "../lib/toolRequestsApi";

/** Stock portrait for the person (Unsplash). If it cannot load, the initials show instead. */
const USER_AVATAR =
  "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=64&h=64&fit=crop&q=80";
/** The company AI's avatar: the Sentry sentinel. While an answer is on its way it thinks: the eye
 * searches faster and a soft ring breathes behind it. Both stop for reduced motion. */
function AiAvatar({ thinking = false }: { thinking?: boolean }) {
  return (
    <span
      role="img"
      aria-label="Company AI"
      className={cn(
        "ai-avatar relative flex size-8 shrink-0 items-center justify-center",
        thinking && "is-thinking",
      )}
    >
      <Sentinel size={24} className="sentinel-sm relative" />
    </span>
  );
}

interface Pending {
  text: string;
  reasons: string[];
  suggestion?: string;
  files?: ReadFile[];
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
  const [pending, setPending] = useState<Pending | null>(null);
  // The answer while it streams in, shown under the chat it belongs to.
  const [live, setLive] = useState<{ chat: string; text: string } | null>(null);
  const [rated, setRated] = useState<number | null>(null);
  const [category, setCategory] = useState("");
  const [sidebar, setSidebar] = useState(
    () => typeof matchMedia === "function" && matchMedia("(min-width: 768px)").matches,
  );
  const [who, setWho] = useState<Identity | null>(null);
  const [requestOpen, setRequestOpen] = useState(false);
  // X29: answers to tool requests, shown on the next message.
  const [notices, setNotices] = useState<string[]>([]);
  const identity = useRef<Identity | null>(null);
  const chatsRef = useRef(chats);
  chatsRef.current = chats;
  const counter = useRef(0);
  // Files to attach to the next message, and the text of files already sent (by turn id). File
  // text lives only in memory for this visit: it is never written to localStorage.
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [limits, setLimits] = useState(DEFAULT_LIMITS);
  const [hint, setHint] = useState(() => uploadHint(window.location.search));
  const turnFiles = useRef(new Map<number, ReadFile[]>());

  useEffect(() => saveChats(chats), [chats]);
  useEffect(() => {
    void fetchFileLimits().then(setLimits);
  }, []);
  useEffect(() => {
    ensureIdentity().then(
      (i) => {
        identity.current ??= i;
        setWho(i);
      },
      () => undefined, // send() reports the failure when the person tries
    );
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

  const accept = limits.types.join(",");
  const fileId = () => `f${makeId()}`;

  /** Checks each file, then has the server read it. Ready files go out with the next message. */
  const addFiles = (picked: File[]) => {
    if (hint) dismissHint(); // the banner has done its job once a file is on its way
    let count = attachments.filter((a) => a.status !== "error").length;
    const added: Attachment[] = [];
    const toRead: [string, File][] = [];
    for (const f of picked) {
      const id = fileId();
      const problem = precheck(f, limits, count);
      if (problem) added.push({ id, name: f.name, status: "error", message: problem });
      else {
        added.push({ id, name: f.name, status: "reading" });
        toRead.push([id, f]);
        count += 1;
      }
    }
    setAttachments((all) => [...all, ...added]);
    for (const [id, f] of toRead)
      void extractFile(f, limits).then((r) =>
        setAttachments((all) =>
          all.map((a) =>
            a.id !== id
              ? a
              : r.ok
                ? {
                    id,
                    status: "ready",
                    name: r.name,
                    text: r.text,
                    chars: r.chars,
                    truncated: r.truncated,
                  }
                : { id, name: f.name, status: "error", message: r.message },
          ),
        ),
      );
  };
  const removeFile = (id: string) => setAttachments((all) => all.filter((a) => a.id !== id));
  const dismissHint = () => {
    setHint(null);
    try {
      window.history.replaceState(window.history.state, "", window.location.pathname);
    } catch {
      // the banner is gone either way
    }
  };
  /** What the gateway checks for a turn: the typed text plus the text of its files. */
  const contentOf = (t: StoredTurn) => {
    const files = turnFiles.current.get(t.id);
    return files ? composeMessage(t.text, files) : t.text;
  };

  /** Sends `text` as a new turn, or retries the last question when `retry` is set. */
  const send = async (
    text: string,
    opts: { ack?: string; retry?: boolean; reroute?: boolean; files?: ReadFile[] } = {},
  ) => {
    const clean = text.trim();
    const fromComposer = !opts.retry && !opts.files;
    const files: ReadFile[] = opts.retry
      ? []
      : (opts.files ??
        attachments.flatMap((a) =>
          a.status === "ready"
            ? [{ name: a.name, text: a.text, chars: a.chars, truncated: a.truncated }]
            : [],
        ));
    if ((!clean && !files.length) || busy) return;
    if (fromComposer && attachments.some((a) => a.status === "reading")) return;
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
    const turnId = makeId();
    if (files.length) turnFiles.current.set(turnId, files);
    const base: StoredTurn[] = opts.retry
      ? before.slice(0, before.findLastIndex((t) => t.from === "user") + 1)
      : [
          ...before,
          {
            id: turnId,
            from: "user",
            text: clean,
            ...(files.length ? { files: files.map(toSent) } : {}),
          },
        ];
    const first = before.length === 0;
    update(id, (c) => ({
      turns: base,
      title: first && !opts.retry ? titleFrom(clean || (files[0]?.name ?? "")) : c.title,
    }));
    if (!opts.retry) setDraft("");
    if (fromComposer) setAttachments([]);
    // Earlier turns that passed untouched. A masked, held or rerouted turn is not sent again, so the
    // gateway never sees the original text twice.
    const untouched: StoredTurn[] = [];
    for (let i = 0; i + 2 < base.length; i += 2) {
      const [q, a] = [base[i], base[i + 1]];
      if (q?.from === "user" && a?.from === "assistant" && (!a.outcome || a.outcome === "allow"))
        untouched.push(q, a);
    }
    const asked = base[base.length - 1];
    const history: ChatTurn[] = [...untouched, ...(asked ? [asked] : [])].map((t) => ({
      role: t.from,
      content: contentOf(t),
    }));
    try {
      identity.current ??= await ensureIdentity();
      const who = identity.current;
      if (!opts.retry)
        void collectOutcomes(who.userId).then((rs) => {
          if (rs.length > 0) setNotices((n) => [...n, ...rs.map(outcomeText)]);
        });
      const chatId = id;
      setLive({ chat: chatId, text: "" });
      const res = await sendChat(who, history, opts.ack, opts.reroute, (text) =>
        setLive({ chat: chatId, text }),
      );
      if (res.kind === "answer")
        append(id, {
          from: "assistant",
          text: res.text,
          outcome: res.outcome,
          reasons: res.reasons,
        });
      else if (res.kind === "warn") {
        const held = opts.retry ? turnFiles.current.get(asked?.id ?? -1) : files;
        // A suggested rewrite covers the whole message, file text included, so it is not offered
        // when files are attached: that text would land in the saved chat.
        setPending({
          text: opts.retry ? (asked?.text ?? clean) : clean,
          reasons: res.reasons,
          suggestion: held?.length ? undefined : res.suggestion,
          ...(held?.length ? { files: held } : {}),
        });
      } else if (res.kind === "block")
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
      setLive(null);
      setBusy(false);
    }
  };

  /** X31: send the held or blocked question to Company AI instead. The gate masks it first. */
  const reroute = () => {
    const q = pending?.text ?? lastUser?.text;
    if (q) void send(q, { retry: true, reroute: true });
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
    const files = turnFiles.current.get(t.id) ?? [];
    setAttachments(files.map((f) => ({ id: fileId(), status: "ready", ...f })));
  };

  return (
    <div className="bg-[#0a0908]">
      <div className="mx-auto flex h-[calc(100dvh-76px)] min-h-[32rem] w-full max-w-[1264px] overflow-hidden px-0 sm:px-4">
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
          <header className="z-10 flex h-14 w-full shrink-0 items-center gap-2 border-b border-ink-200 bg-[#0a0908] px-4">
            <TextureButton
              variant="minimal"
              size="icon"
              aria-label={sidebar ? "Hide chat history" : "Show chat history"}
              aria-expanded={sidebar}
              onClick={() => setSidebar((s) => !s)}
            >
              <PanelLeft className="size-4" aria-hidden="true" />
            </TextureButton>
            <h1 className="min-w-0 truncate text-lg text-ink-900">
              {active?.title ?? "Company AI"}
            </h1>
            <span className="ml-auto hidden shrink-0 text-xs text-ink-600 sm:inline">
              Messages are checked first. Answers come from the company&apos;s own model.
            </span>
          </header>

          {hint ? (
            <UploadBanner
              tool={hint.tool}
              file={hint.file}
              accept={accept}
              onFiles={addFiles}
              onDismiss={dismissHint}
            />
          ) : null}
          {notices.length > 0 ? (
            <div role="status" className="space-y-2 border-b border-ink-200 bg-brand-50 px-4 py-2">
              {notices.map((n) => (
                <p key={n} className="text-sm text-ink-900">
                  {n}
                </p>
              ))}
            </div>
          ) : null}
          {who && !requestOpen ? (
            <p className="border-b border-ink-200 px-4 py-1 text-sm text-ink-600">
              Need another AI tool?{" "}
              <button
                type="button"
                onClick={() => setRequestOpen(true)}
                className="min-h-11 font-medium text-brand-700 underline underline-offset-2"
              >
                Request approval
              </button>
            </p>
          ) : null}

          {empty ? (
            <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-4 pb-10">
              <div className="w-full max-w-3xl">
                <div className="mb-6 flex flex-col items-center gap-3 text-center">
                  <Sentinel size={72} />
                  <h2 className="text-3xl text-ink-900">What can I help with?</h2>
                </div>
                <PromptBox
                  value={draft}
                  onChange={setDraft}
                  onSend={() => void send(draft)}
                  busy={busy}
                  attachments={attachments}
                  accept={accept}
                  maxChars={limits.maxChars}
                  onAddFiles={addFiles}
                  onRemoveFile={removeFile}
                />
                {requestOpen && who ? (
                  <div className="mt-4">
                    <RequestToolForm
                      userId={who.userId}
                      team={who.team}
                      onClose={() => setRequestOpen(false)}
                    />
                  </div>
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
                              {t.files?.length ? (
                                <ul
                                  className="flex max-w-full flex-wrap justify-end gap-2"
                                  aria-label="Attached files"
                                >
                                  {t.files.map((f) => (
                                    <li
                                      key={f.name}
                                      className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-ink-200 bg-ink-50 px-3 py-1.5 text-xs text-ink-700"
                                    >
                                      <FileText className="size-3.5 shrink-0" aria-hidden="true" />
                                      <span className="truncate font-medium">{f.name}</span>
                                      {f.truncated ? (
                                        <span className="shrink-0">· Shortened</span>
                                      ) : null}
                                    </li>
                                  ))}
                                </ul>
                              ) : null}
                              {t.text ? (
                                <MessageContent className="max-w-[85%] whitespace-pre-wrap rounded-3xl bg-brand-100 px-5 py-2.5 text-ink-900 sm:max-w-[75%]">
                                  {t.text}
                                </MessageContent>
                              ) : null}
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
                          <AiAvatar />
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
                                <OutcomeChip
                                  outcome={t.outcome}
                                  detail={
                                    asked?.files?.length ? fileSummary(asked.files) : undefined
                                  }
                                />
                                {t.outcome === "rerouted" ? (
                                  <p className="text-sm text-ink-600">Answered by Company AI</p>
                                ) : null}
                                {t.reasons?.length ? (
                                  <Tool
                                    className="w-full max-w-md"
                                    toolPart={{
                                      type: "sentry_check",
                                      state: "output-available",
                                      input: {
                                        message: `${asked?.text.length ?? 0} characters`,
                                        ...(asked?.files?.length
                                          ? {
                                              files: asked.files
                                                .map(
                                                  (f) =>
                                                    `${f.name} (${f.chars.toLocaleString("en")} characters${f.truncated ? ", shortened" : ""})`,
                                                )
                                                .join(", "),
                                            }
                                          : {}),
                                      },
                                      output: {
                                        decision: t.outcome,
                                        why: t.reasons.map(explainReason).join("; "),
                                      },
                                    }}
                                  />
                                ) : null}
                              </div>
                            ) : null}
                            {last && t.outcome === "block" && !busy ? (
                              <div className="flex flex-wrap gap-2">
                                <TextureButton variant="primary" onClick={reroute}>
                                  Send it to Company AI instead
                                </TextureButton>
                                {!requestOpen ? (
                                  <TextureButton
                                    variant="secondary"
                                    onClick={() => setRequestOpen(true)}
                                  >
                                    Request approval for the tool you wanted
                                  </TextureButton>
                                ) : null}
                              </div>
                            ) : null}
                            {!t.failed ? (
                              <AnswerActions
                                text={t.text}
                                last={last}
                                canRetry={!busy && last && !!lastUser}
                                onRetry={() =>
                                  lastUser && void send(lastUser.text, { retry: true })
                                }
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

                    {busy && live?.chat === activeId && live.text ? (
                      <Message className="mx-auto flex w-full max-w-3xl items-start gap-3 px-2">
                        <AiAvatar thinking />
                        <div className="flex min-w-0 flex-1 flex-col gap-2">
                          <MessageContent
                            markdown
                            className="streaming-caret flex-1 rounded-lg bg-transparent p-0 text-ink-900 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-5"
                          >
                            {live.text}
                          </MessageContent>
                          <span className="sr-only" role="status">
                            Company AI is writing the answer
                          </span>
                        </div>
                      </Message>
                    ) : busy ? (
                      <div
                        className="mx-auto flex w-full max-w-3xl items-center gap-3 px-2 text-sm text-ink-600"
                        role="status"
                      >
                        <AiAvatar thinking />
                        <ThinkingBar className="w-auto" text="Thinking on the company server" />
                        <Loader variant="typing" size="sm" />
                      </div>
                    ) : null}

                    {pending ? (
                      <div className="mx-auto w-full max-w-3xl px-2">
                        <WarnCard
                          reasons={pending.reasons}
                          suggestion={pending.suggestion}
                          busy={busy}
                          onUseSuggestion={
                            pending.suggestion
                              ? () => void send(pending.suggestion ?? "")
                              : undefined
                          }
                          onEdit={() => {
                            setDraft(pending.text);
                            setPending(null);
                          }}
                          onSendAnyway={(reason) =>
                            void send(pending.text, { ack: reason, files: pending.files })
                          }
                          onCancel={() => setPending(null)}
                          onReroute={reroute}
                        />
                      </div>
                    ) : null}
                    {requestOpen && who ? (
                      <div className="mx-auto w-full max-w-3xl px-2">
                        <RequestToolForm
                          userId={who.userId}
                          team={who.team}
                          onClose={() => setRequestOpen(false)}
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
              <div className="z-10 shrink-0 bg-[#0a0908] px-3 pb-3 md:px-5 md:pb-5">
                <div className="mx-auto max-w-3xl">
                  <PromptBox
                    value={draft}
                    onChange={setDraft}
                    onSend={() => void send(draft)}
                    busy={busy}
                    attachments={attachments}
                    accept={accept}
                    maxChars={limits.maxChars}
                    onAddFiles={addFiles}
                    onRemoveFile={removeFile}
                  />
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
