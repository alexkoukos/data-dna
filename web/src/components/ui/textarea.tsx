import * as React from "react";
import { cn } from "@/lib/utils";

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex field-sizing-content min-h-16 w-full rounded-md border border-ink-200 bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none placeholder:text-ink-500 focus-visible:border-ink-400 focus-visible:ring-[3px] focus-visible:ring-ink-400/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-block-solid aria-invalid:ring-block-solid/20 md:text-sm ",
        className,
      )}
      {...props}
    />
  );
}

export { Textarea };
