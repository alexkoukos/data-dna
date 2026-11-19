"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * The Sentry button. Simple on purpose: a flat fill, one border, a clear hover, a visible focus ring,
 * 44 px high. `primary` is Sentry amber with ink text (one per screen), `secondary` is the neutral
 * default, `minimal` is quiet, `destructive` is red, `accent` is ink, `icon` is a round icon button.
 * (Kept under the TextureButton name so every screen keeps its import.)
 */
const buttonVariants = cva(
  "inline-flex min-h-11 select-none items-center justify-center gap-2 max-w-full whitespace-normal text-center rounded-[10px] border px-5 text-sm font-semibold transition-colors duration-150 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "border-brand-700/50 bg-brand-600 text-ink-900 hover:bg-brand-500 active:bg-brand-700/40",
        accent:
          "border-brand-600 bg-brand-600 text-primary-foreground hover:bg-brand-500 active:bg-brand-400",
        destructive:
          "border-block-solid bg-block-solid text-white hover:bg-block-fg active:bg-block-fg",
        secondary: "border-ink-300 bg-surface text-ink-900 hover:bg-ink-50 active:bg-ink-100",
        minimal:
          "border-transparent bg-transparent text-ink-900 hover:bg-ink-100 active:bg-ink-200",
        icon: "min-w-11 rounded-full border-ink-300 bg-surface px-0 text-ink-900 hover:bg-ink-50 active:bg-ink-100",
      },
      size: {
        sm: "px-4 text-xs",
        default: "",
        lg: "px-6 text-base",
        icon: "size-11 px-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  },
);

export interface UnifiedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "accent" | "destructive" | "minimal" | "icon";
  size?: "default" | "sm" | "lg" | "icon";
  asChild?: boolean;
}

const TextureButton = React.forwardRef<HTMLButtonElement, UnifiedButtonProps>(
  (
    { children, variant = "primary", size = "default", asChild = false, className, ...props },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size }), className)} ref={ref} {...props}>
        {children}
      </Comp>
    );
  },
);

TextureButton.displayName = "TextureButton";

export { TextureButton };
