import { useEffect, useRef, useState, type ReactNode } from "react";
import { Check, Copy, RefreshCcw, ThumbsDown, ThumbsUp, type LucideIcon } from "lucide-react";

/**
 * Chat building blocks in the shape of the 21st.dev "AI actions" example: a Conversation holds
 * Messages, each Message has a MessageContent and, for the assistant, a row of Actions.
 * Plain CSS (see "Company chat" in ui.css), lucide icons, no remote images.
 */
export function Conversation({ children }: { children: ReactNode }) {
  return (
    <div className="conv" role="log" aria-live="polite" aria-label="Conversation">
      {children}
    </div>
  );
}

export function ConversationContent({ children }: { children: ReactNode }) {
  return <div className="conv-content">{children}</div>;
}

export function Message({ from, children }: { from: "user" | "assistant"; children: ReactNode }) {
  return <div className={`msg ${from}`}>{children}</div>;
}

export function MessageContent({ children }: { children: ReactNode }) {
  return <div className="msg-bubble">{children}</div>;
}

/** Who is speaking: the bee for the company AI, a monogram for the person. */
export function Avatar({ from }: { from: "user" | "assistant" }) {
  return from === "assistant" ? (
    <span className="avatar-chat bee-avatar" aria-hidden="true">
      <img src="/brand/hive-guard-bee.svg" alt="" width={22} />
    </span>
  ) : (
    <span className="avatar-chat me-avatar" aria-hidden="true">
      You
    </span>
  );
}

export function Actions({ children }: { children: ReactNode }) {
  return (
    <div className="msg-actions" role="group" aria-label="Message actions">
      {children}
    </div>
  );
}

export function Action({
  label,
  icon: Icon,
  onClick,
  pressed,
  disabled,
}: {
  label: string;
  icon: LucideIcon;
  onClick?: () => void;
  pressed?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className="act"
      aria-label={label}
      title={label}
      aria-pressed={pressed}
      disabled={disabled}
      onClick={onClick}
    >
      <Icon size={16} aria-hidden="true" />
    </button>
  );
}

/** Retry, Like, Dislike, Copy for one assistant answer. Like and Dislike are marks on this screen only. */
export function AnswerActions({
  text,
  onRetry,
  canRetry,
}: {
  text: string;
  onRetry: () => void;
  canRetry: boolean;
}) {
  const [vote, setVote] = useState<"up" | "down" | null>(null);
  const [copied, setCopied] = useState(false);
  const timer = useRef(0);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* the text stays selectable; nothing else to do */
    }
  };

  return (
    <Actions>
      <Action label="Ask again" icon={RefreshCcw} onClick={onRetry} disabled={!canRetry} />
      <Action
        label="Good answer"
        icon={ThumbsUp}
        pressed={vote === "up"}
        onClick={() => setVote(vote === "up" ? null : "up")}
      />
      <Action
        label="Not a good answer"
        icon={ThumbsDown}
        pressed={vote === "down"}
        onClick={() => setVote(vote === "down" ? null : "down")}
      />
      <Action
        label={copied ? "Copied" : "Copy answer"}
        icon={copied ? Check : Copy}
        onClick={copy}
      />
      <span className="sr-only" role="status">
        {copied ? "Answer copied" : ""}
      </span>
    </Actions>
  );
}
