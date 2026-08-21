import { Input } from "@/components/ui/input";
import { useTranslations } from "next-intl";

export type HistorySort = "recent" | "score";

export function HistoryFilters({
  query,
  status,
  sort,
  onQueryChange,
  onStatusChange,
  onSortChange,
}: {
  query: string;
  status: string;
  sort: HistorySort;
  onQueryChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onSortChange: (value: HistorySort) => void;
}) {
  const t = useTranslations("history");
  return (
    <div className="grid gap-3 border-b border-[var(--color-border)] pb-4 md:grid-cols-[minmax(0,1fr)_150px_150px]">
      <Input
        aria-label={t("search")}
        placeholder={t("searchPlaceholder")}
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
      />
      <label className="text-xs text-[var(--color-text-muted)]">
        {t("status")}
        <select
          aria-label={t("status")}
          value={status}
          onChange={(event) => onStatusChange(event.target.value)}
          className="mt-1 h-9 w-full rounded-[var(--radius-panel)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
        >
          <option value="all">{t("allStatuses")}</option>
          <option value="completed">{t("completed")}</option>
          <option value="running">{t("running")}</option>
          <option value="failed">{t("failed")}</option>
          <option value="cancelled">{t("cancelled")}</option>
          <option value="interrupted">{t("interrupted")}</option>
        </select>
      </label>
      <label className="text-xs text-[var(--color-text-muted)]">
        {t("sort")}
        <select
          aria-label={t("sort")}
          value={sort}
          onChange={(event) => onSortChange(event.target.value as HistorySort)}
          className="mt-1 h-9 w-full rounded-[var(--radius-panel)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
        >
          <option value="recent">{t("recent")}</option>
          <option value="score">{t("qualityScore")}</option>
        </select>
      </label>
    </div>
  );
}
