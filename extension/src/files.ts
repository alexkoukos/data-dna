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
  /** Opens the company AI with these files, so they are not lost. */
  onOpenCompanyAi: (attachments: Attachment[]) => void;
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
export interface FileGuard {
  /** Reviews files. Resolves true when they may go on, false when they were stopped. */
  review: (files: File[]) => Promise<boolean>;
}

/**
 * Holds back files until the company server has read them. Two doors, one decision:
 * the page's own events (file picker, drag and drop, paste) remove the file before the site sees it,
 * and the upload hook (src/upload-bridge) stops the upload itself, whatever way the file got there.
 * A verdict is remembered for a minute so one file never asks twice.
 */
export function installFileGuard(opts: FileGuardOptions): FileGuard {
  let passing = false;
  const verdicts = new Map<string, { ok: boolean; at: number }>();
  const keyOf = (f: File) => `${f.name}|${f.size}|${f.lastModified}`;

  async function decide(list: File[]): Promise<boolean> {
    const attachments = await Promise.all(list.map(toAttachment));
    const out = await opts.check(attachments);
    if (!out || !out.action) {
      // We could not read the file. A confidential file must not slip through unseen, so ask.
      const choice = await opts.overlay.card({
        action: "warn",
        title: "Hive could not check this file",
        reasons: [
          "The company server could not be reached, so this file was not checked.",
          "Make sure the server is running. Remove the file, or attach it anyway on your own risk.",
        ],
        askReason: true,
        buttons: [
          { id: "remove", label: "Remove file", kind: "primary" },
          { id: "attach", label: "Attach anyway", kind: "danger" },
        ],
      });
      return choice.id === "attach";
    }
    if (out.action === "allow") {
      opts.overlay.note(
        `Checked by Hive: ${list.length === 1 ? (list[0]?.name ?? "1 file") : `${list.length} files`}, nothing sensitive found.`,
        3000,
      );
      return true;
    }
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
      return choice.id === "attach";
    }

    void opts.overlay
      .card({
        action: "block",
        title: "File not attached",
        reasons: [
          "This file is confidential and must stay inside the company.",
          "The company AI can read it safely. Open it there and your file comes with you.",
        ],
        details: reasons,
        buttons: [
          { id: "close", label: "Close", kind: "secondary" },
          { id: "ask", label: "Open company AI", kind: "primary" },
        ],
      })
      .then((choice) => {
        if (choice.id === "ask") opts.onOpenCompanyAi(attachments);
      });
    return false;
  }

  async function review(files: File[]): Promise<boolean> {
    const list = readable(files);
    if (!list.length) return true;
    const now = Date.now();
    const known = list.map((f) => verdicts.get(keyOf(f)));
    if (known.every((v) => v && now - v.at < 60_000)) return known.every((v) => v?.ok);
    const ok = await decide(list);
    for (const f of list) verdicts.set(keyOf(f), { ok, at: Date.now() });
    return ok;
  }

  async function guard(files: File[], release: () => void, drop: () => void) {
    if (await review(files)) release();
    else drop();
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

  // A file copied in Finder and pasted. Finder also puts the file name on the clipboard as text.
  document.addEventListener(
    "paste",
    (e) => {
      const files = [...(e.clipboardData?.files ?? [])];
      if (passing || !readable(files).length) return;
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

  return { review };
}
