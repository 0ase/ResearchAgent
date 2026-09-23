import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils/cn";

type AlertTone = "info" | "success" | "warning" | "error";

const toneStyles: Record<AlertTone, string> = {
  info: "border-[var(--color-info-border)] bg-[var(--color-info-subtle)] text-[var(--color-info)]",
  success:
    "border-[var(--color-success-border)] bg-[var(--color-success-subtle)] text-[var(--color-success)]",
  warning:
    "border-[var(--color-warning-border)] bg-[var(--color-warning-subtle)] text-[var(--color-warning)]",
  error:
    "border-[var(--color-error-border)] bg-[var(--color-error-subtle)] text-[var(--color-error)]",
};

const icons = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
};

export function InlineAlert({
  children,
  tone = "info",
  className,
}: {
  children: ReactNode;
  tone?: AlertTone;
  className?: string;
}) {
  const Icon = icons[tone];
  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        "flex items-start gap-2 rounded-[var(--radius-panel)] border px-3 py-2.5 text-[13px]",
        toneStyles[tone],
        className,
      )}
    >
      <Icon aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{children}</span>
    </div>
  );
}
