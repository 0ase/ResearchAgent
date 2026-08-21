import { Badge } from "@/components/ui/badge";
import type { ResearchPaper } from "@/features/papers/paper-model";
import { useTranslations } from "next-intl";

export function PaperRow({
  paper,
  selected = false,
  onSelect,
}: {
  paper: ResearchPaper;
  selected?: boolean;
  onSelect?: (paper: ResearchPaper) => void;
}) {
  const t = useTranslations("papers");
  return (
    <article
      className={
        selected
          ? "border-l-2 border-[var(--color-primary)] bg-[var(--color-primary-subtle)]"
          : "border-l-2 border-transparent"
      }
    >
      <button
        type="button"
        aria-label={`Paper: ${paper.title}`}
        onClick={() => onSelect?.(paper)}
        className="w-full px-4 py-3 text-left hover:bg-[var(--color-surface-subtle)]"
      >
        <div className="flex items-start justify-between gap-3">
          <h3 className="line-clamp-3 text-sm font-medium text-[var(--color-text)]">
            {paper.title}
          </h3>
          <Badge variant="neutral">{paper.source}</Badge>
        </div>
        <p className="mt-1 line-clamp-1 text-xs text-[var(--color-text-muted)]">
          {paper.authors.join(", ") || t("unknownAuthors")}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-subtle)]">
          {paper.year ? <span>{paper.year}</span> : null}
          <span>
            {paper.citationCount === null
              ? "—"
              : `${paper.citationCount} ${t("citations").toLowerCase()}`}
          </span>
          {paper.relevanceScore !== null ? (
            <span>
              {t("relevanceValue", { value: paper.relevanceScore.toFixed(1) })}
            </span>
          ) : null}
          {paper.reportCitationCount > 0 ? (
            <Badge variant="blue">
              {t("citedInReport", { count: paper.reportCitationCount })}
            </Badge>
          ) : null}
          {paper.selected ? (
            <Badge variant="success">{t("selected")}</Badge>
          ) : null}
          {paper.fullTextStatus === "abstract_only" ? (
            <Badge variant="warning">{t("abstractOnly")}</Badge>
          ) : null}
          {paper.fullTextStatus === "full" ? (
            <Badge variant="success">{t("fullTextAvailable")}</Badge>
          ) : null}
          {paper.fullTextStatus === "full_no_abstract" ? (
            <Badge variant="warning">{t("fullNoAbstract")}</Badge>
          ) : null}
          {paper.fullTextStatus === "unavailable" ? (
            <Badge variant="error">{t("unavailable")}</Badge>
          ) : null}
          {paper.fullTextStatus === "pdf_failed" ? (
            <Badge variant="error">{t("pdfFailed")}</Badge>
          ) : null}
        </div>
      </button>
    </article>
  );
}
