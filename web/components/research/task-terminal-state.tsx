import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";

export function TaskTerminalState({
  status,
  onRetry,
}: {
  status: "completed" | "cancelled" | "interrupted";
  onRetry?: () => void;
}) {
  const t = useTranslations("task");
  const common = useTranslations("common");
  const copy = {
    completed: [t("completedTitle"), t("completedDescription")],
    cancelled: [t("cancelledTitle"), t("cancelledDescription")],
    interrupted: [t("interruptedTitle"), t("interruptedDescription")],
  } as const;
  const [title, description] = copy[status];

  return (
    <section className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="text-base font-semibold text-[var(--color-text)]">
        {title}
      </h2>
      <p className="mt-1 text-sm text-[var(--color-text-muted)]">
        {description}
      </p>
      <div className="mt-4 flex gap-2">
        {onRetry && status !== "completed" ? (
          <Button onClick={onRetry}>{t("retryResearch")}</Button>
        ) : null}
        <Link
          href="/history"
          className="inline-flex h-9 items-center rounded-[var(--radius-control)] border border-[var(--color-border-strong)] px-3 text-[13px] font-medium text-[var(--color-text)]"
        >
          {common("history")}
        </Link>
      </div>
    </section>
  );
}
