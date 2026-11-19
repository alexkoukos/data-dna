import { useRef } from "react";
import { Upload, X } from "lucide-react";
import { TextureButton } from "@/components/ui/texture-button";

interface Props {
  tool: string;
  file: string;
  accept: string;
  onFiles: (files: File[]) => void;
  onDismiss: () => void;
}

/**
 * Presentational: shown when the browser extension stopped a file upload on an outside AI tool
 * and sent the person here. Browsers cannot hand the file over, so the person picks it again.
 */
export function UploadBanner({ tool, file, accept, onFiles, onDismiss }: Props) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <section
      aria-label="Upload the file here instead"
      className="flex items-start gap-3 border-b border-ink-200 bg-brand-50 px-4 py-2"
    >
      <Upload className="mt-3 size-4 shrink-0 text-ink-900" aria-hidden="true" />
      <div className="flex min-w-0 flex-1 flex-col gap-2 py-2 sm:flex-row sm:items-center sm:gap-4">
        <p className="min-w-0 flex-1 text-sm text-ink-900">
          You tried to upload <strong className="break-all font-semibold">{file}</strong> to {tool}.
          Upload it here instead: it is checked first and you will still get an answer.
        </p>
        <TextureButton
          variant="secondary"
          size="sm"
          className="min-h-11 w-fit shrink-0"
          onClick={() => input.current?.click()}
        >
          Choose the file
        </TextureButton>
        <input
          ref={input}
          type="file"
          multiple
          accept={accept}
          className="hidden"
          aria-hidden="true"
          tabIndex={-1}
          onChange={(e) => {
            const picked = [...(e.target.files ?? [])];
            e.target.value = "";
            if (picked.length) onFiles(picked);
          }}
        />
      </div>
      <TextureButton
        variant="minimal"
        size="icon"
        aria-label="Dismiss this message"
        className="shrink-0 rounded-full"
        onClick={onDismiss}
      >
        <X className="size-4" aria-hidden="true" />
      </TextureButton>
    </section>
  );
}
