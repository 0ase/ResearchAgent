import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils/cn";

type BadgeVariant = "neutral" | "blue" | "success" | "warning" | "error";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variants: Record<BadgeVariant, string> = {
  neutral:
    "border-[var(--color-border)] bg-[var(--color-surface-subtle)] text-[var(--color-text-muted)]",
  blue: "border-[#bfdbfe] bg-[var(--color-primary-subtle)] text-[var(--color-primary-hover)]",
  success: "border-[#bbf7d0] bg-[#f0fdf4] text-[var(--color-success)]",
  warning: "border-[#fed7aa] bg-[#fff7ed] text-[var(--color-warning)]",
  error: "border-[#fecaca] bg-[#fef2f2] text-[var(--color-error)]",
};

export function Badge({
  className,
  variant = "neutral",
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center rounded-full border px-2 text-xs font-medium",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
