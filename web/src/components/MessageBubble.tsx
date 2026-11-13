import { WHAT_WE_DID, explainReason } from "../lib/explain";
import { Thyro } from "./Thyro";
import { OutcomeChip, type Outcome } from "./OutcomeChip";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  outcome?: Outcome;
  detail?: string;
  reasons?: string[];
  alternative?: string;
}

/** Presentational: one message, its outcome chip, and a "Why?" disclosure when something happened. */
export function MessageBubble({ message }: { message: ChatMessage }) {
  const mine = message.role === "user";
  const hasWhy = message.outcome && message.outcome !== "allow";
  return (
    <li className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 ${mine ? "bg-brand-600 text-white" : "border border-ink-200 bg-white text-ink-900"}`}
      >
        <p className="whitespace-pre-wrap break-words text-base leading-relaxed">{message.text}</p>
        {message.outcome ? (
          <div className="mt-2 flex items-center gap-3 rounded-md bg-ink-50 p-2 text-ink-900">
            <Thyro pose={message.outcome} />
            <OutcomeChip outcome={message.outcome} detail={message.detail} />
          </div>
        ) : null}
        {hasWhy ? (
          <details className={`mt-2 text-sm ${mine ? "text-brand-50" : "text-ink-700"}`}>
            <summary className="min-h-11 cursor-pointer py-3 font-medium underline-offset-2 hover:underline">
              Why?
            </summary>
            <ul className="list-disc space-y-1 pb-2 pl-5">
              {(message.reasons ?? []).map((r) => (
                <li key={r}>{explainReason(r)}</li>
              ))}
            </ul>
            <p className="pb-2">{WHAT_WE_DID[message.outcome!]}</p>
            {message.alternative ? <p className="pb-2">{message.alternative}</p> : null}
          </details>
        ) : null}
      </div>
    </li>
  );
}
