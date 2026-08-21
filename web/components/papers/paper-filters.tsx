import { Input } from "@/components/ui/input";
import { useTranslations } from "next-intl";

export type PaperSort = "relevance" | "citations" | "year";

export function PaperFilters({
  query,
  source,
  sort,
  selectedOnly,
  citedOnly,
  fromYear,
  toYear,
  sources,
  onQueryChange,
  onSourceChange,
  onSortChange,
  onSelectedOnlyChange,
  onCitedOnlyChange,
  onFromYearChange,
  onToYearChange,
  yearRangeInvalid,
}: {
  query: string;
  source: string;
  sort: PaperSort;
  selectedOnly: boolean;
  citedOnly: boolean;
  fromYear: string;
  toYear: string;
  sources: string[];
  onQueryChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onSortChange: (value: PaperSort) => void;
  onSelectedOnlyChange: (value: boolean) => void;
  onCitedOnlyChange: (value: boolean) => void;
  onFromYearChange: (value: string) => void;
  onToYearChange: (value: string) => void;
  yearRangeInvalid?: boolean;
}) {
  const t = useTranslations("papers");
  return (
    <div className="grid gap-3 border-b border-[var(--color-border)] pb-4 md:grid-cols-[minmax(0,1fr)_150px_150px]">
      <Input
        aria-label={t("search")}
        placeholder={t("searchPlaceholder")}
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
      />
      <label className="text-xs text-[var(--color-text-muted)]">
        {t("source")}
        <select
          aria-label={t("source")}
          value={source}
          onChange={(event) => onSourceChange(event.target.value)}
          className="mt-1 h-9 w-full rounded-[var(--radius-panel)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
        >
          <option value="all">{t("allSources")}</option>
          {sources.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs text-[var(--color-text-muted)]">
        {t("sort")}
        <select
          aria-label={t("sort")}
          value={sort}
          onChange={(event) => onSortChange(event.target.value as PaperSort)}
          className="mt-1 h-9 w-full rounded-[var(--radius-panel)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
        >
          <option value="relevance">{t("relevance")}</option>
          <option value="citations">{t("citations")}</option>
          <option value="year">{t("year")}</option>
        </select>
      </label>
      <label className="text-xs text-[var(--color-text-muted)]">
        {t("fromYear")}
        <input
          aria-label={t("fromYear")}
          type="number"
          inputMode="numeric"
          min={1900}
          max={new Date().getFullYear()}
          value={fromYear}
          onChange={(event) => onFromYearChange(event.target.value)}
          className="mt-1 h-9 w-full rounded-[var(--radius-panel)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
        />
      </label>
      <label className="text-xs text-[var(--color-text-muted)]">
        {t("toYear")}
        <input
          aria-label={t("toYear")}
          type="number"
          inputMode="numeric"
          min={1900}
          max={new Date().getFullYear()}
          value={toYear}
          onChange={(event) => onToYearChange(event.target.value)}
          className="mt-1 h-9 w-full rounded-[var(--radius-panel)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-sm text-[var(--color-text)]"
        />
      </label>
      <div className="flex flex-wrap items-center gap-3 md:col-span-3">
        <label className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
          <input
            aria-label={t("selectedOnly")}
            type="checkbox"
            checked={selectedOnly}
            onChange={(event) => onSelectedOnlyChange(event.target.checked)}
          />{" "}
          {t("selectedOnly")}
        </label>
        <label className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
          <input
            aria-label={t("citedOnly")}
            type="checkbox"
            checked={citedOnly}
            onChange={(event) => onCitedOnlyChange(event.target.checked)}
          />{" "}
          {t("citedOnly")}
        </label>
        {yearRangeInvalid ? (
          <span role="alert" className="text-xs text-[var(--color-error)]">
            {t("yearRangeInvalid")}
          </span>
        ) : null}
      </div>
    </div>
  );
}
