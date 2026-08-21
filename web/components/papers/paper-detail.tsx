"use client";

import ExternalLink from "next/link";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { ResearchPaper } from "@/features/papers/paper-model";
import { useUiStore } from "@/stores/ui-store";

export type PaperCitationLink = {
  citationId: string;
  displayNumber?: number | null;
};

export function PaperDetail({
  paper,
  citations = [],
}: {
  paper: ResearchPaper | null;
  citations?: PaperCitationLink[];
}) {
  const t = useTranslations("papers");
  const selectObject = useUiStore((state) => state.selectObject);
  const setContextTab = useUiStore((state) => state.setContextTab);
  if (!paper) {
    return (
      <aside
        aria-label={t("detailTitle")}
        className="p-5 text-sm text-[var(--color-text-muted)]"
      >
        {t("selectToInspect")}
      </aside>
    );
  }

  return (
    <aside aria-label={t("detailTitle")} className="space-y-4 p-5">
      <div>
        <p className="text-xs uppercase tracking-[0.08em] text-[var(--color-primary)]">
          {t("detailTitle")}
        </p>
        <h2 className="mt-2 text-lg font-semibold text-[var(--color-text)]">
          {paper.title}
        </h2>
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge>{paper.source}</Badge>
        {paper.year ? <Badge>{paper.year}</Badge> : null}
        {paper.selected ? (
          <Badge variant="success">{t("selected")}</Badge>
        ) : null}
        {paper.fullTextStatus === "full" ? (
          <Badge variant="success">{t("fullTextAvailable")}</Badge>
        ) : null}
        {paper.fullTextStatus === "full_no_abstract" ? (
          <Badge variant="warning">{t("fullNoAbstract")}</Badge>
        ) : null}
        {paper.fullTextStatus === "abstract_only" ? (
          <Badge variant="warning">{t("abstractOnly")}</Badge>
        ) : null}
        {paper.fullTextStatus === "unavailable" ? (
          <Badge variant="error">{t("unavailable")}</Badge>
        ) : null}
        {paper.fullTextStatus === "pdf_failed" ? (
          <Badge variant="error">{t("pdfFailed")}</Badge>
        ) : null}
      </div>
      <dl className="grid gap-2 text-sm">
        <div>
          <dt className="text-xs text-[var(--color-text-subtle)]">
            {t("authors")}
          </dt>
          <dd className="text-[var(--color-text-muted)]">
            {paper.authors.join(", ") || t("unknownAuthors")}
          </dd>
        </div>
        {paper.doi ? (
          <div>
            <dt className="text-xs text-[var(--color-text-subtle)]">DOI</dt>
            <dd className="text-[var(--color-text-muted)]">{paper.doi}</dd>
          </div>
        ) : null}
        <div>
          <dt className="text-xs text-[var(--color-text-subtle)]">
            {t("citations")}
          </dt>
          <dd className="text-[var(--color-text-muted)]">
            {paper.citationCount ?? "—"}
          </dd>
        </div>
        {paper.relevanceScore !== null ? (
          <div>
            <dt className="text-xs text-[var(--color-text-subtle)]">
              {t("relevance")}
            </dt>
            <dd className="text-[var(--color-text-muted)]">
              {paper.relevanceScore.toFixed(1)}
            </dd>
          </div>
        ) : null}
      </dl>
      <div>
        <h3 className="text-sm font-medium text-[var(--color-text)]">
          {t("abstract")}
        </h3>
        <p className="mt-1 text-sm leading-6 text-[var(--color-text-muted)]">
          {paper.abstract || t("noAbstract")}
        </p>
      </div>
      {paper.fullTextStatus === "abstract_only" ? (
        <p className="text-sm text-[var(--color-warning)]">
          {t("abstractOnlyNotice")}
        </p>
      ) : null}
      {paper.fullTextStatus === "pdf_failed" ? (
        <p className="text-sm text-[var(--color-error)]">
          {t("pdfFailedNotice")}
        </p>
      ) : null}
      {paper.fullTextStatus === "full_no_abstract" ? (
        <p className="text-sm text-[var(--color-warning)]">
          {t("fullNoAbstractNotice")}
        </p>
      ) : null}
      {paper.fullTextStatus === "unavailable" ? (
        <p className="text-sm text-[var(--color-error)]">
          {t("unavailableNotice")}
        </p>
      ) : null}
      {paper.pdfUrl ? (
        <ExternalLink
          href={paper.pdfUrl}
          target="_blank"
          rel="noreferrer noopener"
          className="text-sm font-medium text-[var(--color-primary)]"
        >
          {t("openPdf")}
        </ExternalLink>
      ) : null}
      {citations.length ? (
        <div className="border-t border-[var(--color-border)] pt-3">
          <h3 className="text-sm font-medium text-[var(--color-text)]">
            {t("reportCitations")}
          </h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {citations.map((citation) => (
              <button
                key={citation.citationId}
                type="button"
                className="rounded-[var(--radius-control)] border border-[var(--color-border-strong)] px-2 py-1 text-xs text-[var(--color-primary)] hover:bg-[var(--color-primary-subtle)]"
                onClick={() => {
                  selectObject(citation.citationId);
                  setContextTab("evidence");
                }}
              >
                {t("citationNumber", {
                  number: citation.displayNumber ?? citation.citationId,
                })}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
