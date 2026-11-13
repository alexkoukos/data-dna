import { useState } from "react";
import { registerDocument } from "../lib/securityApi";

const field =
  "mt-1 min-h-11 w-full rounded-md border border-ink-300 bg-white px-3 text-sm text-ink-900";

/** Register a document by pasting its text or choosing a PDF, DOCX or text file. */
export function AddDocument({ onAdded }: { onAdded: () => void }) {
  const [title, setTitle] = useState("");
  const [sensitivity, setSensitivity] = useState("confidential");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    const form = new FormData();
    form.set("title", title.trim());
    form.set("sensitivity", sensitivity);
    if (file) form.set("file", file);
    else form.set("text", text);
    try {
      const made = await registerDocument(form);
      setMessage({ ok: true, text: `Added "${made.title}" (${made.chunks} parts).` });
      setTitle("");
      setText("");
      setFile(null);
      onAdded();
    } catch (err) {
      setMessage({ ok: false, text: err instanceof Error ? err.message : "That did not work." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="mb-4 rounded-lg border border-ink-200 bg-white p-4">
      <summary className="min-h-11 cursor-pointer py-2 text-sm font-semibold text-ink-900">
        Add a document
      </summary>
      <form onSubmit={submit} className="mt-2">
        <label className="block text-sm font-medium text-ink-700">
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} className={field} />
        </label>
        <label className="mt-3 block text-sm font-medium text-ink-700">
          Sensitivity
          <select
            value={sensitivity}
            onChange={(e) => setSensitivity(e.target.value)}
            className={field}
          >
            <option value="internal">Internal</option>
            <option value="confidential">Confidential</option>
            <option value="restricted">Restricted</option>
          </select>
        </label>
        <label className="mt-3 block text-sm font-medium text-ink-700">
          File (PDF, DOCX, TXT or Markdown)
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className={field}
          />
        </label>
        <label className="mt-3 block text-sm font-medium text-ink-700">
          Or paste the text
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            disabled={file !== null}
            className={`${field} py-2`}
          />
        </label>
        <button
          type="submit"
          disabled={busy || !title.trim() || (!file && !text.trim())}
          className="mt-3 min-h-11 rounded-md bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-ink-200 disabled:text-ink-700"
        >
          {busy ? "Adding…" : "Add the document"}
        </button>
        {message ? (
          <p
            role={message.ok ? "status" : "alert"}
            className={`mt-2 text-sm font-semibold ${message.ok ? "text-allow-fg" : "text-block-fg"}`}
          >
            {message.text}
          </p>
        ) : null}
      </form>
    </details>
  );
}
