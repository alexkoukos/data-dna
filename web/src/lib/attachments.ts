/**
 * Files attached in Company Chat. The brain reads each file into text (`/api/v1/files/extract`);
 * the text then travels inside the message, so the gateway checks it exactly like typed text
 * before any model sees it. File text is kept in memory only, never in localStorage.
 */

export interface FileLimits {
  maxBytes: number;
  maxFiles: number;
  maxChars: number;
  types: string[];
}

export const DEFAULT_LIMITS: FileLimits = {
  maxBytes: 10 * 1024 * 1024,
  maxFiles: 3,
  maxChars: 30_000,
  types: [".csv", ".docx", ".md", ".pdf", ".txt"],
};

/** A file the brain has read: what goes into the message. */
export interface ReadFile {
  name: string;
  text: string;
  chars: number;
  truncated: boolean;
}

/** What a stored turn remembers about a file: its name and size, never its text. */
export interface SentFile {
  name: string;
  chars: number;
  truncated: boolean;
}

export type Attachment =
  | { id: string; name: string; status: "reading" }
  | ({ id: string; status: "ready" } & ReadFile)
  | { id: string; name: string; status: "error"; message: string };

export const TYPE_NAMES = "PDF, Word (.docx), text, Markdown or CSV";

export function formatBytes(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${Math.round(bytes / (1024 * 1024))} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

const suffix = (name: string) => {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(dot).toLowerCase() : "";
};

/**
 * Quick checks before the upload, so a wrong file fails at once. The brain checks again by
 * content (a renamed file is caught there). Returns a message to show, or null when it can go.
 */
export function precheck(file: File, limits: FileLimits, alreadyAttached: number): string | null {
  if (!limits.types.includes(suffix(file.name)))
    return `${file.name} was not added. Attach a ${TYPE_NAMES} file.`;
  if (file.size > limits.maxBytes)
    return `${file.name} is larger than ${formatBytes(limits.maxBytes)}. Split it or attach only the part you need.`;
  if (file.size === 0) return `${file.name} is empty. Check that it is the right file.`;
  if (alreadyAttached >= limits.maxFiles)
    return `${file.name} was not added. You can attach up to ${limits.maxFiles} ${limits.maxFiles === 1 ? "file" : "files"} to one message; remove one first.`;
  return null;
}

/** The name as it appears in the message header: no brackets or line breaks, at most 200 characters. */
export const safeName = (name: string) => name.replace(/[\]\r\n]/g, "_").slice(0, 200) || "file";

export function fileBlock(f: ReadFile): string {
  const name = safeName(f.name);
  const cut = f.truncated
    ? `\n[Only the first ${f.text.length.toLocaleString("en")} of ${f.chars.toLocaleString("en")} characters of this file were included.]`
    : "";
  return `[File: ${name}]\n${f.text}${cut}\n[End of file: ${name}]`;
}

/** The message the gateway checks and the model reads: the question, then each file. */
export function composeMessage(prompt: string, files: ReadFile[]): string {
  return [prompt.trim(), ...files.map(fileBlock)].filter(Boolean).join("\n\n");
}

export const toSent = (f: ReadFile): SentFile => ({
  name: f.name,
  chars: f.chars,
  truncated: f.truncated,
});

/** "report.pdf" or "report.pdf +2 more", for the outcome chip. */
export function fileSummary(files: { name: string }[]): string {
  if (!files.length) return "";
  const first = files[0]!.name;
  return files.length === 1 ? first : `${first} +${files.length - 1} more`;
}

const TOOL_NAMES: Record<string, string> = {
  chatgpt: "ChatGPT",
  claude: "Claude",
  gemini: "Gemini",
};

/** Reads `?from=<tool>&file=<name>` from the address the extension opened. */
export function uploadHint(search: string): { tool: string; file: string } | null {
  const q = new URLSearchParams(search);
  const file = (q.get("file") ?? "")
    .replace(/[\r\n]/g, " ")
    .trim()
    .slice(0, 120);
  if (!file) return null;
  const from = (q.get("from") ?? "").trim();
  const tool = TOOL_NAMES[from.toLowerCase()] ?? (from.slice(0, 40) || "an outside AI tool");
  return { tool, file };
}
