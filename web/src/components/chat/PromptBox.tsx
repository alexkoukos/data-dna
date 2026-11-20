import { ArrowUp, Paperclip } from "lucide-react";
import { FileUpload, FileUploadContent, FileUploadTrigger } from "@/components/ui/file-upload";
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input";
import { PromptSuggestion } from "@/components/ui/prompt-suggestion";
import { TextureButton } from "@/components/ui/texture-button";
import { suggestFor } from "../../lib/chatPrompts";
import { typeNames, type Attachment } from "../../lib/attachments";
import { AttachmentChips } from "./AttachmentChips";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  busy: boolean;
  placeholder?: string;
  attachments?: Attachment[];
  accept?: string;
  maxChars?: number;
  onAddFiles?: (files: File[]) => void;
  onRemoveFile?: (id: string) => void;
}

/**
 * The prompt input of the prompt-kit chat: a textarea with actions (attach files, send) and an
 * autocomplete that highlights what has been typed in matching library prompts.
 * Files can be attached with the button (keyboard) or dropped anywhere on the page. The page reads
 * them on the server and sends their text inside the message, so the usual check sees them.
 */
export function PromptBox({
  value,
  onChange,
  onSend,
  busy,
  placeholder = "Ask the company AI",
  attachments = [],
  accept = ".pdf,.docx,.txt,.md,.csv",
  maxChars = 30_000,
  onAddFiles,
  onRemoveFile,
}: Props) {
  const suggestions = busy || attachments.length ? [] : suggestFor(value);
  const kinds = typeNames(accept.split(","));
  const reading = attachments.some((a) => a.status === "reading");
  const hasFiles = attachments.some((a) => a.status === "ready");
  const canSend = !busy && !reading && (!!value.trim() || hasFiles);
  const send = () => {
    if (canSend) onSend();
  };

  return (
    <div className="w-full">
      <PromptInput
        isLoading={busy}
        value={value}
        onValueChange={onChange}
        onSubmit={send}
        className="relative z-10 w-full rounded-3xl border border-ink-300 bg-surface p-0 pt-1 shadow-xs focus-within:border-ink-900"
      >
        <div className="flex flex-col">
          <AttachmentChips
            items={attachments}
            maxChars={maxChars}
            onRemove={(id) => onRemoveFile?.(id)}
          />
          <PromptInputTextarea
            aria-label="Your question"
            placeholder={placeholder}
            className="prompt-textarea min-h-[44px] pt-3 pl-4 text-base leading-[1.3] outline-none focus-visible:shadow-none focus-visible:outline-none sm:text-base md:text-base"
          />
          <PromptInputActions className="mt-3 flex w-full items-center justify-between gap-2 px-3 pb-3">
            <div className="flex items-center gap-2">
              {onAddFiles ? (
                <FileUpload onFilesAdded={onAddFiles} accept={accept} disabled={busy}>
                  <PromptInputAction tooltip={`Attach files (${kinds})`}>
                    <FileUploadTrigger asChild>
                      <TextureButton
                        variant="secondary"
                        size="icon"
                        aria-label="Attach files"
                        disabled={busy}
                        className="rounded-full"
                      >
                        <Paperclip className="size-4" aria-hidden="true" />
                      </TextureButton>
                    </FileUploadTrigger>
                  </PromptInputAction>
                  <FileUploadContent className="bg-ink-50/90">
                    <div className="rounded-3xl border-2 border-dashed border-ink-400 bg-surface px-8 py-6 text-center">
                      <p className="text-lg font-semibold text-ink-900">
                        Drop files to attach them
                      </p>
                      <p className="mt-1 text-sm text-ink-700">
                        {kinds}. They are checked before anything is sent.
                      </p>
                    </div>
                  </FileUploadContent>
                </FileUpload>
              ) : null}
            </div>
            <PromptInputAction tooltip="Send (Enter)">
              <TextureButton
                variant="primary"
                size="icon"
                aria-label="Send"
                disabled={!canSend}
                onClick={send}
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
