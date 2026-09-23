import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils/cn";

type BadgeVariant =
  "neutral" | "accent" | "info" | "blue" | "success" | "warning" | "error";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variants: Record<BadgeVariant, string> = {
  neutral:
    "border-[var(--color-border)] bg-[var(--color-surface-subtle)] text-[var(--color-text-muted)]",
  accent:
    "border-[var(--color-primary-border)] bg-[var(--color-primary-subtle)] text-[var(--color-primary)]",
  info: "border-[var(--color-info-border)] bg-[var(--color-info-subtle)] text-[var(--color-info)]",
  blue: "border-[var(--color-info-border)] bg-[var(--color-info-subtle)] text-[var(--color-info)]",
  success:
    "border-[var(--color-success-border)] bg-[var(--color-success-subtle)] text-[var(--color-success)]",
  warning:
    "border-[var(--color-warning-border)] bg-[var(--color-warning-subtle)] text-[var(--color-warning)]",
  error:
    "border-[var(--color-error-border)] bg-[var(--color-error-subtle)] text-[var(--color-error)]",
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
