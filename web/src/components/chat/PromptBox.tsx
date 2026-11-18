import { useRef, useState } from "react";
import { ArrowUp, FileText, Plus, X } from "lucide-react";
import { FileUpload, FileUploadTrigger } from "@/components/ui/file-upload";
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { PromptSuggestion } from "@/components/ui/prompt-suggestion";
import { TextureButton } from "@/components/ui/texture-button";
import { suggestFor } from "../../lib/chatPrompts";
import type { ChatAttachment } from "../../lib/chatApi";

const MAX_FILE_CHARS = 20_000;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

async function toBase64(f: File): Promise<string> {
  const bytes = new Uint8Array(await f.arrayBuffer());
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(bin);
}

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  busy: boolean;
  placeholder?: string;
  /** Files the server reads (PDF, DOCX, images). Text files are put into the message itself. */
  attachments?: ChatAttachment[];
  onAttachmentsChange?: (a: ChatAttachment[]) => void;
}

/**
 * The prompt input of the prompt-kit chat: a textarea with actions (add a text file, send) and an
 * autocomplete that highlights what has been typed in matching library prompts.
 * Added files are read here in the browser and become part of the message, so the usual check sees them.
 */
export function PromptBox({
  value,
  onChange,
  onSend,
  busy,
  placeholder = "Ask the company AI",
  attachments = [],
  onAttachmentsChange,
}: Props) {
  const [files, setFiles] = useState<string[]>([]);
  const [fileNote, setFileNote] = useState("");
  const textRef = useRef(value);
  textRef.current = value;
  const suggestions = busy ? [] : suggestFor(value);

  const addFiles = async (picked: File[]) => {
    setFileNote("");
    let text = textRef.current;
    const names: string[] = [];
    const added: ChatAttachment[] = [];
    for (const f of picked) {
      if (onAttachmentsChange && /\.(pdf|docx|png|jpe?g)$/i.test(f.name)) {
        if (f.size > MAX_FILE_BYTES) {
          setFileNote(`${f.name} was not added. Files can be up to 10 MB.`);
        } else {
          added.push({ filename: f.name, content_base64: await toBase64(f) });
        }
        continue;
      }
      if (f.size > 1_000_000 || !/\.(txt|md|csv|json|log)$/i.test(f.name)) {
        setFileNote(
          `${f.name} was not added. Use a PDF, DOCX, image or text file (.txt, .md, .csv, .json, .log).`,
        );
        continue;
      }
      const body = (await f.text()).slice(0, MAX_FILE_CHARS);
      text += `${text ? "\n\n" : ""}[File: ${f.name}]\n${body}`;
      names.push(f.name);
    }
    if (added.length) onAttachmentsChange?.([...attachments, ...added]);
    if (names.length) {
      onChange(text);
      setFiles((all) => [...all, ...names]);
    }
  };

  return (
    <div className="w-full">
      <PromptInput
        isLoading={busy}
        value={value}
        onValueChange={onChange}
        onSubmit={onSend}
        className="relative z-10 w-full rounded-3xl border border-ink-300 bg-white p-0 pt-1 shadow-xs focus-within:border-ink-900"
      >
        <div className="flex flex-col">
          {attachments.length ? (
            <ul className="flex flex-wrap gap-2 px-4 pt-3" aria-label="Attached files">
              {attachments.map((a, i) => (
                <li
                  key={`${a.filename}-${i}`}
                  className="inline-flex items-center gap-1.5 rounded-full border border-ink-200 bg-ink-50 py-1 pl-3 pr-1 text-xs text-ink-700"
                >
                  <FileText className="size-3.5" aria-hidden="true" />
                  {a.filename}
                  <button
                    type="button"
                    aria-label={`Remove ${a.filename}`}
                    className="grid size-6 place-items-center rounded-full hover:bg-ink-200"
                    onClick={() => onAttachmentsChange?.(attachments.filter((_, j) => j !== i))}
                  >
                    <X className="size-3" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {files.length ? (
            <ul className="flex flex-wrap gap-2 px-4 pt-3" aria-label="Added files">
              {files.map((n, i) => (
                <li
                  key={`${n}-${i}`}
                  className="inline-flex items-center gap-1.5 rounded-full border border-ink-200 bg-ink-50 py-1 pl-3 pr-1 text-xs text-ink-700"
                >
                  <FileText className="size-3.5" aria-hidden="true" />
                  {n}
                  <button
                    type="button"
                    aria-label={`Forget ${n} (its text stays in the message until you delete it)`}
                    className="grid size-6 place-items-center rounded-full hover:bg-ink-200"
                    onClick={() => setFiles((all) => all.filter((_, j) => j !== i))}
                  >
                    <X className="size-3" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          <PromptInputTextarea
            aria-label="Your question"
            placeholder={placeholder}
            className="prompt-textarea min-h-[44px] pt-3 pl-4 text-base leading-[1.3] outline-none focus-visible:shadow-none focus-visible:outline-none sm:text-base md:text-base"
          />
          <PromptInputActions className="mt-3 flex w-full items-center justify-between gap-2 px-3 pb-3">
            <div className="flex items-center gap-2">
              <FileUpload
                onFilesAdded={(f) => void addFiles(f)}
                accept=".txt,.md,.csv,.json,.log,.pdf,.docx,.png,.jpg,.jpeg"
              >
                <PromptInputAction tooltip="Add a file">
                  <FileUploadTrigger asChild>
                    <TextureButton
                      variant="secondary"
                      size="icon"
                      aria-label="Add a file"
                      className="rounded-full"
                    >
                      <Plus className="size-4" aria-hidden="true" />
                    </TextureButton>
                  </FileUploadTrigger>
                </PromptInputAction>
              </FileUpload>
            </div>
            <PromptInputAction tooltip="Send (Enter)">
              <TextureButton
                variant="primary"
                size="icon"
                aria-label="Send"
                disabled={busy || (!value.trim() && !attachments.length)}
                onClick={onSend}
                className="rounded-full"
              >
                {busy ? (
                  <span className="size-3 rounded-[2px] bg-ink-900" aria-hidden="true" />
                ) : (
                  <ArrowUp className="size-4" aria-hidden="true" />
                )}
              </TextureButton>
            </PromptInputAction>
          </PromptInputActions>
        </div>
      </PromptInput>
      {fileNote ? (
        <p role="status" className="mt-2 px-2 text-sm text-block-fg">
          {fileNote}
        </p>
      ) : null}
      {suggestions.length ? (
        <div className="mt-2 w-full space-y-1" aria-label="Suggestions">
          {suggestions.map((s) => (
            <PromptSuggestion
              key={s}
              highlight={value}
              className="flex h-auto w-full flex-wrap text-left"
              onClick={() => onChange(s)}
            >
              {s}
            </PromptSuggestion>
          ))}
        </div>
      ) : null}
    </div>
  );
}
