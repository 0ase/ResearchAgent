import { WifiOff } from "lucide-react";
import { useTranslations } from "next-intl";

export function TaskOfflineState() {
  const t = useTranslations("task");
  return (
    <div className="flex items-center gap-2 rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface-subtle)] px-3 py-2 text-sm text-[var(--color-text-muted)]">
      <WifiOff aria-hidden="true" className="h-4 w-4" />
      {t("offline")}
    </div>
  );
}
