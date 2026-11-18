/**
 * Runs inside the page itself (MAIN world), so it can stop an upload whatever way the file got
 * there: a picker the page built out of sight, a drop, a paste. It wraps fetch and XMLHttpRequest;
 * when a request carries a file, it asks the extension (the other content script) first, and the
 * request goes out only if the answer is yes. Nothing is read from the page and nothing is sent
 * anywhere by this script: the extension does the checking.
 */
const READABLE = /\.(pdf|docx|txt|md|csv|json|log|png|jpe?g)$/i;
const MAX_BYTES = 10 * 1024 * 1024;
const MIME_NAME: Record<string, string> = {
  "application/pdf": "upload.pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "upload.docx",
  "text/plain": "upload.txt",
  "image/png": "upload.png",
  "image/jpeg": "upload.jpg",
};

export default defineContentScript({
  matches: [
    "http://localhost:3100/*",
    "https://chatgpt.com/*",
    "https://chat.openai.com/*",
    "https://claude.ai/*",
    "https://gemini.google.com/*",
  ],
  world: "MAIN",
  runAt: "document_start",
  main() {
    let next = 0;
    const waiting = new Map<number, (ok: boolean) => void>();

    window.addEventListener("message", (e) => {
      if (e.source !== window || e.data?.hive !== "verdict") return;
      waiting.get(e.data.id)?.(e.data.ok === true);
      waiting.delete(e.data.id);
    });

    /** Files in a request body, with a name we can read. */
    function filesIn(body: unknown): File[] {
      const out: File[] = [];
      const add = (v: unknown) => {
        if (!(v instanceof Blob) || v.size > MAX_BYTES || v.size === 0) return;
        const name = v instanceof File && v.name ? v.name : (MIME_NAME[v.type] ?? "");
        if (!name || !READABLE.test(name)) return;
        out.push(
          v instanceof File && v.name ? v : new File([v], name, { type: v.type, lastModified: 0 }),
        );
      };
      if (body instanceof FormData) body.forEach((v) => add(v));
      else add(body);
      return out;
    }

    /** Asks the extension. Resolves true to let the request go. Waits up to 30 s, then lets it go. */
    function ask(files: File[]): Promise<boolean> {
      return new Promise((resolve) => {
        const id = ++next;
        const timer = window.setTimeout(() => {
          waiting.delete(id);
          resolve(true);
        }, 30_000);
        waiting.set(id, (ok) => {
          window.clearTimeout(timer);
          resolve(ok);
        });
        window.postMessage({ hive: "files", id, files }, "*");
      });
    }

    const realFetch = window.fetch;
    window.fetch = async function (this: unknown, input: RequestInfo | URL, init?: RequestInit) {
      const files = filesIn(init?.body);
      if (files.length && !(await ask(files))) {
        throw new TypeError("Hive stopped this upload: the file must stay inside the company.");
      }
      return realFetch.call(this, input, init);
    };

    const realSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function (
      this: XMLHttpRequest,
      body?: Document | XMLHttpRequestBodyInit | null,
    ) {
      const files = filesIn(body);
      if (!files.length) return realSend.call(this, body);
      void ask(files).then((ok) => {
        if (ok) realSend.call(this, body);
        else {
          this.dispatchEvent(new ProgressEvent("error"));
          this.dispatchEvent(new ProgressEvent("loadend"));
        }
      });
    };
  },
});
