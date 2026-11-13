/** Presentational: placeholder with the same shape as the chat while the personal key is created. */
export function ChatSkeleton() {
  return (
    <div role="status" aria-label="Getting your chat ready" className="animate-pulse space-y-3">
      <div className="h-24 rounded-2xl bg-ink-200" />
      <div className="h-12 rounded-xl bg-ink-200" />
    </div>
  );
}
