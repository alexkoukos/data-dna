import { DEFAULT_LIMITS, formatBytes, type FileLimits, type ReadFile } from "./attachments";

/** The upload limits set on the server (env), or the defaults when it cannot be reached. */
export async function fetchFileLimits(): Promise<FileLimits> {
  try {
    const res = await fetch("/api/v1/files/limits");
    if (!res.ok) return DEFAULT_LIMITS;
    const b = (await res.json()) as Partial<{
      max_bytes: number;
      max_files: number;
      max_chars: number;
      types: string[];
    }>;
    const num = (v: unknown, fallback: number) =>
      typeof v === "number" && Number.isFinite(v) && v > 0 ? v : fallback;
    return {
      maxBytes: num(b.max_bytes, DEFAULT_LIMITS.maxBytes),
      maxFiles: num(b.max_files, DEFAULT_LIMITS.maxFiles),
      maxChars: num(b.max_chars, DEFAULT_LIMITS.maxChars),
      types:
        Array.isArray(b.types) && b.types.every((t) => typeof t === "string")
          ? b.types
          : DEFAULT_LIMITS.types,
    };
  } catch {
    return DEFAULT_LIMITS;
  }
}

export type ExtractResult = ({ ok: true } & ReadFile) | { ok: false; message: string };

/** Ask the brain to read one file into text. It decides nothing and stores nothing. */
export async function extractFile(file: File, limits: FileLimits): Promise<ExtractResult> {
  const body = new FormData();
  body.append("file", file, file.name);
  let res: Response;
  try {
    res = await fetch("/api/v1/files/extract", { method: "POST", body });
  } catch {
    return {
      ok: false,
      message: `We could not reach the server to read ${file.name}. Check your connection and try again.`,
    };
  }
  if (res.ok) {
    const b = (await res.json()) as { text: string; chars: number; truncated: boolean };
    return { ok: true, name: file.name, text: b.text, chars: b.chars, truncated: b.truncated };
  }
  if (res.status === 413)
    return {
      ok: false,
      message: `${file.name} is larger than ${formatBytes(limits.maxBytes)}. Split it or attach only the part you need.`,
    };
  try {
    const b = (await res.json()) as { detail?: { message?: string } };
    if (typeof b.detail?.message === "string")
      return { ok: false, message: `${file.name}: ${b.detail.message}` };
  } catch {
    // fall through to the generic message
  }
  return {
    ok: false,
    message: `${file.name} could not be read. Try again, or paste the text into the message.`,
  };
}
