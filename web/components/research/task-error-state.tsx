import { Button } from "@/components/ui/button";
import { InlineAlert } from "@/components/ui/inline-alert";
import { useTranslations } from "next-intl";

export function TaskErrorState({
  code,
  message,
  retryable,
  onRetry,
}: {
  code?: string | null;
  message?: string | null;
  retryable?: boolean;
  onRetry?: () => void;
}) {
  const t = useTranslations("task");
  const common = useTranslations("common");
  return (
    <section className="space-y-4">
      <InlineAlert tone="error">{t("errorTitle")}</InlineAlert>
      <div className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <details className="text-xs text-[var(--color-text-muted)]">
          <summary className="cursor-pointer">
            {common("technicalDetails")}
          </summary>
          <p className="mt-2">
            {t("errorCode")}: {code ?? "UNKNOWN_ERROR"}
          </p>
          {message ? <p className="mt-1">{message}</p> : null}
        </details>
        {retryable && onRetry ? (
          <Button className="mt-4" onClick={onRetry}>
            {t("retryResearch")}
          </Button>
        ) : (
          <p className="mt-4 text-sm text-[var(--color-text-muted)]">
            {t("preservedInHistory")}
          </p>
        )}
      </div>
    </section>
  );
}
