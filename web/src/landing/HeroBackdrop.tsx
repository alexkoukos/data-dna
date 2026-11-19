import { DotPattern } from "@/components/ui/dot-pattern";
import { cn } from "@/lib/utils";

/** The hero background: a night field of cyan dots that fades toward the edges, with a soft beacon glow. */
export function HeroBackdrop({ className = "" }: { className?: string }) {
  return (
    <div className={`hero-backdrop ${className}`.trim()} aria-hidden="true">
      <DotPattern
        cx={1}
        cy={1}
        cr={1}
        className={cn(
          "fill-brand-600/60 md:fill-brand-600/75",
          "[mask-image:radial-gradient(1100px_circle_at_60%_45%,white,transparent)]",
        )}
      />
    </div>
  );
}
