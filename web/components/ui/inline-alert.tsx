import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils/cn";

type AlertTone = "info" | "success" | "warning" | "error";

const toneStyles: Record<AlertTone, string> = {
  info: "border-[#bfdbfe] bg-[var(--color-primary-subtle)] text-[var(--color-primary-hover)]",
  success: "border-[#bbf7d0] bg-[#f0fdf4] text-[var(--color-success)]",
  warning: "border-[#fed7aa] bg-[#fff7ed] text-[var(--color-warning)]",
  error: "border-[#fecaca] bg-[#fef2f2] text-[var(--color-error)]",
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
