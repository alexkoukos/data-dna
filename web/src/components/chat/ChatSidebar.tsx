import { useMemo, useState } from "react";
import { MoreHorizontal, Pencil, PlusIcon, Search, Trash, X } from "lucide-react";
import { TextureButton } from "@/components/ui/texture-button";
import { cn } from "@/lib/utils";
import { groupByPeriod, type Chat } from "../../lib/chatStore";

interface Props {
  chats: Chat[];
  activeId: string | null;
  open: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}

/** Chat history, grouped by when each chat last moved. Search, rename and delete work on this browser's chats. */
export function ChatSidebar({
  chats,
  activeId,
  open,
  onSelect,
  onNew,
  onRename,
  onDelete,
  onClose,
}: Props) {
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const shown = q ? chats.filter((c) => c.title.toLowerCase().includes(q)) : chats;
    return groupByPeriod(shown);
  }, [chats, query]);

  return (
    <>
      {open ? (
        <button
          type="button"
          aria-label="Close chat history"
          className="fixed inset-0 z-20 bg-black/30 md:hidden"
          onClick={onClose}
        />
      ) : null}
      <aside
        aria-label="Chat history"
        className={cn(
          "z-30 flex w-72 shrink-0 flex-col border-r border-ink-200 bg-surface transition-[margin,transform] duration-200",
          "max-md:fixed max-md:inset-y-16 max-md:left-0",
          open
            ? "translate-x-0"
            : "-translate-x-full max-md:pointer-events-none md:-ml-72 md:translate-x-0",
        )}
      >
        <div className="flex items-center justify-between gap-2 px-4 py-4">
          <p className="font-display text-lg text-ink-900">Chats</p>
          <TextureButton
            variant="minimal"
            size="icon"
            aria-label={searching ? "Close search" : "Search chats"}
            aria-pressed={searching}
            onClick={() => {
              setSearching((s) => !s);
              setQuery("");
            }}
          >
            {searching ? (
              <X className="size-4" aria-hidden="true" />
            ) : (
              <Search className="size-4" aria-hidden="true" />
            )}
          </TextureButton>
        </div>

        <div className="px-4">
          <TextureButton variant="secondary" className="mb-3 w-full" onClick={onNew}>
            <PlusIcon className="size-4" aria-hidden="true" />
            New chat
          </TextureButton>
          {searching ? (
            <>
              <label htmlFor="chat-search" className="sr-only">
                Search chats
              </label>
              <input
                id="chat-search"
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search chats"
                className="mb-3 min-h-11 w-full rounded-[10px] border border-ink-300 bg-surface px-3 text-sm"
              />
            </>
          ) : null}
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-4" aria-label="Your chats">
          {groups.length === 0 ? (
            <p className="px-3 py-6 text-sm text-ink-600">
              {query ? "No chat matches that." : "Your chats appear here after the first question."}
            </p>
          ) : null}
          {groups.map((g) => (
            <section key={g.period} className="mb-3">
              <h2 className="!font-sans px-3 py-1 !text-xs !font-semibold uppercase tracking-wide text-ink-500">
                {g.period}
              </h2>
              <ul>
                {g.chats.map((c) => (
                  <li key={c.id} className="group relative">
                    {renaming === c.id ? (
                      <form
                        className="px-1 py-1"
                        onSubmit={(e) => {
                          e.preventDefault();
                          onRename(c.id, draftTitle.trim() || c.title);
                          setRenaming(null);
                        }}
                      >
                        <label htmlFor={`rename-${c.id}`} className="sr-only">
                          Chat title
                        </label>
                        <input
                          id={`rename-${c.id}`}
                          autoFocus
                          value={draftTitle}
                          onChange={(e) => setDraftTitle(e.target.value)}
                          onBlur={() => setRenaming(null)}
                          onKeyDown={(e) => e.key === "Escape" && setRenaming(null)}
                          className="min-h-11 w-full rounded-[10px] border border-brand-700 bg-surface px-3 text-sm"
                        />
                      </form>
                    ) : (
                      <div
                        className={cn(
                          "flex items-center rounded-[10px]",
                          c.id === activeId ? "bg-brand-100" : "hover:bg-ink-100",
                        )}
                      >
                        <button
                          type="button"
                          aria-current={c.id === activeId ? "page" : undefined}
                          onClick={() => onSelect(c.id)}
                          className="min-h-11 min-w-0 flex-1 truncate px-3 text-left text-sm text-ink-900"
                        >
                          {c.title}
                        </button>
                        <button
                          type="button"
                          aria-label={`More for ${c.title}`}
                          aria-expanded={menuFor === c.id}
                          onClick={() => setMenuFor(menuFor === c.id ? null : c.id)}
                          className="grid size-11 shrink-0 place-items-center rounded-[10px] text-ink-600 hover:text-ink-900"
                        >
                          <MoreHorizontal className="size-4" aria-hidden="true" />
                        </button>
                      </div>
                    )}
                    {menuFor === c.id ? (
                      <div
                        role="menu"
                        className="absolute right-2 top-11 z-10 w-40 rounded-[12px] border border-ink-200 bg-surface p-1 shadow-md"
                      >
                        <button
                          type="button"
                          role="menuitem"
                          className="flex min-h-11 w-full items-center gap-2 rounded-[8px] px-3 text-sm hover:bg-ink-100"
                          onClick={() => {
                            setDraftTitle(c.title);
                            setRenaming(c.id);
                            setMenuFor(null);
                          }}
                        >
                          <Pencil className="size-4" aria-hidden="true" />
                          Rename
                        </button>
                        <button
                          type="button"
                          role="menuitem"
                          className="flex min-h-11 w-full items-center gap-2 rounded-[8px] px-3 text-sm text-block-fg hover:bg-block-bg"
                          onClick={() => {
                            onDelete(c.id);
                            setMenuFor(null);
                          }}
                        >
                          <Trash className="size-4" aria-hidden="true" />
                          Delete
                        </button>
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </nav>
      </aside>
    </>
  );
}
