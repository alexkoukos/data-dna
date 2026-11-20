/** Company Chat on the default local stack, used when the server did not send its own address. */
export const DEFAULT_COMPANY_CHAT = "http://localhost:3000/chat";

/**
 * The Company Chat address for a file the extension stopped: `?from=<tool>&file=<name>`, so the
 * chat can say what happened. Only an http(s) address is used; anything else falls back to the
 * default. The file itself cannot be handed over (browsers do not allow it), only its name.
 */
export function companyChatUrl(base: string | undefined, tool: string, file: string): string {
  let url: URL;
  try {
    url = new URL(base || DEFAULT_COMPANY_CHAT);
    if (url.protocol !== "https:" && url.protocol !== "http:") throw new Error("scheme");
  } catch {
    url = new URL(DEFAULT_COMPANY_CHAT);
  }
  url.search = "";
  url.hash = "";
  url.searchParams.set("from", tool.toLowerCase().slice(0, 40));
  url.searchParams.set("file", file.slice(0, 120));
  return url.toString();
}
