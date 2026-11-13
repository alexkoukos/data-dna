import { Thyro } from "./Thyro";

/** Presentational: placeholder with the same shape as the chat while the personal key is created. */
export function ChatSkeleton() {
  return (
    <div role="status" aria-label="Getting your chat ready" className="space-y-3">
      <div className="flex items-center gap-4">
        <Thyro pose="thinking" size={220} />
        <p className="text-ink-600">Opening the gate…</p>
      </div>
      <div className="animate-pulse space-y-3">
        <div className="h-24 rounded-lg bg-ink-200" />
        <div className="h-12 rounded-lg bg-ink-200" />
      </div>
    </div>
  );
}
