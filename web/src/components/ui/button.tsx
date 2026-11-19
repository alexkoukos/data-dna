import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";

import { cn } from "@/lib/utils";

/**
 * The shadcn Button that the prompt-kit components import, in the Sentry button style (the same flat
 * look as TextureButton): amber `default`, neutral `outline` and `secondary`, quiet `ghost`, red
 * `destructive`. Every size keeps a 44 px touch target.
 */
const buttonVariants = cva(
  "inline-flex shrink-0 select-none items-center justify-center gap-2 whitespace-nowrap rounded-[10px] border text-sm font-semibold transition-colors duration-150 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "border-brand-700/50 bg-brand-600 text-ink-900 hover:bg-brand-500 active:bg-brand-700/40",
        destructive: "border-block-solid bg-block-solid text-white hover:bg-block-fg",
        outline: "border-ink-300 bg-surface text-ink-900 hover:bg-ink-50 active:bg-ink-100",
        secondary: "border-ink-200 bg-ink-100 text-ink-900 hover:bg-ink-200",
        ghost: "border-transparent bg-transparent text-ink-900 hover:bg-ink-100 active:bg-ink-200",
        link: "border-transparent bg-transparent text-brand-700 underline-offset-4 hover:underline",
      },
      size: {
        default: "min-h-11 px-5",
        xs: "min-h-11 px-3 text-xs",
        sm: "min-h-11 px-4 text-xs",
        lg: "min-h-11 px-6 text-base",
        icon: "size-11 px-0",
        "icon-xs": "size-11 px-0",
        "icon-sm": "size-11 px-0",
        "icon-lg": "size-11 px-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : "button";

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
