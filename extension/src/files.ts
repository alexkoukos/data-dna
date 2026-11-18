import type { Overlay } from "./overlay";
import type { CheckResult } from "./types";

/** What the brain can read (services/brain/src/brain/documents/extract.py). */
const READABLE = /\.(pdf|docx|txt|md|csv|json|log|png|jpe?g)$/i;
const MAX_BYTES = 10 * 1024 * 1024;

export interface Attachment {
  filename: string;
  content_base64: string;
}

export interface FileGuardOptions {
  overlay: Overlay;
  /** Asks the company server. Null means it could not be reached. */
  check: (attachments: Attachment[]) => Promise<Partial<CheckResult> | null>;
  onEvent: (action: string, category?: string) => void;
  onOpenCompanyAi: () => void;
}

export async function toAttachment(file: File): Promise<Attachment> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return { filename: file.name, content_base64: btoa(bin) };
}

export function readable(files: File[]): File[] {
  return files.filter((f) => READABLE.test(f.name) && f.size <= MAX_BYTES);
}

function transfer(files: File[]): DataTransfer {
  const dt = new DataTransfer();
  for (const f of files) dt.items.add(f);
  return dt;
}

/**
 * Holds back files the person attaches (picker, drag and drop, paste) until the company server
 * has read them. Fails open when the server cannot be reached, like the text check outside
 * fail-closed categories. No selectors here: file inputs and drop events are the same on every site.
 */
export function installFileGuard(opts: FileGuardOptions): void {
  let passing = false;

  async function guard(files: File[], release: () => void, drop: () => void) {
    const list = readable(files);
    if (!list.length) return release();
    const out = await opts.check(await Promise.all(list.map(toAttachment)));
    if (!out || !out.action || out.action === "allow") return release();
    opts.onEvent(out.action, out.findings?.[0]?.category ?? "document");
    const reasons = out.reasons?.length
      ? out.reasons
      : ["This file may contain data that must stay inside the company."];

    if (out.action === "warn" || out.action === "mask") {
      const choice = await opts.overlay.card({
        action: "warn",
        title: "Check before attaching this file",
        reasons: ["This file may contain sensitive data."],
        details: reasons,
        askReason: true,
        buttons: [
          { id: "remove", label: "Remove file", kind: "primary" },
          { id: "attach", label: "Attach anyway", kind: "danger" },
        ],
      });
      if (choice.id === "attach") release();
      else drop();
      return;
    }

    drop();
    const choice = await opts.overlay.card({
      action: "block",
      title: "File not attached",
      reasons: [
        "This file is confidential and must stay inside the company.",
        "Use the company AI to work with it.",
      ],
      details: reasons,
      buttons: [
        { id: "close", label: "Close", kind: "secondary" },
        { id: "ask", label: "Open company AI", kind: "primary" },
      ],
    });
    if (choice.id === "ask") opts.onOpenCompanyAi();
  }

  // File picker.
  document.addEventListener(
    "change",
    (e) => {
      const input = e.target;
      if (passing || !(input instanceof HTMLInputElement) || input.type !== "file") return;
      const files = [...(input.files ?? [])];
      if (!files.length) return;
      e.stopImmediatePropagation();
      void guard(
        files,
        () => {
          passing = true;
          try {
            input.dispatchEvent(new Event("change", { bubbles: true }));
          } finally {
            passing = false;
          }
        },
        () => {
          input.value = "";
        },
      );
    },
    true,
  );

  // Drag and drop.
  document.addEventListener(
    "drop",
    (e) => {
      const files = [...(e.dataTransfer?.files ?? [])];
      if (passing || !files.length) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      const target = e.target;
      if (!(target instanceof EventTarget)) return;
      void guard(
        files,
        () => {
          passing = true;
          try {
            target.dispatchEvent(
              new DragEvent("drop", {
                bubbles: true,
                cancelable: true,
                dataTransfer: transfer(files),
              }),
            );
          } finally {
            passing = false;
          }
        },
        () => undefined,
      );
    },
    true,
  );

  // A copied file pasted in. Pasted text is handled by the text check.
  document.addEventListener(
    "paste",
    (e) => {
      const files = [...(e.clipboardData?.files ?? [])];
      if (passing || !files.length || e.clipboardData?.getData("text/plain")) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      const target = e.target;
      if (!(target instanceof EventTarget)) return;
      void guard(
        files,
        () => {
          passing = true;
          try {
            target.dispatchEvent(
              new ClipboardEvent("paste", {
                bubbles: true,
                cancelable: true,
                clipboardData: transfer(files),
              }),
            );
          } finally {
            passing = false;
          }
        },
        () => undefined,
      );
    },
    true,
  );
}
