import { forwardRef } from "react";
import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils/cn";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "min-h-24 w-full resize-y rounded-[var(--radius-panel)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-2.5 text-sm leading-relaxed text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-subtle)] transition-colors focus-visible:border-[var(--color-primary)] focus-visible:ring-2 focus-visible:ring-[var(--color-primary-subtle)] disabled:cursor-not-allowed disabled:bg-[var(--color-surface-subtle)]",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";
