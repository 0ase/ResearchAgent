"use client";

import { AlertTriangle, ExternalLink } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { EvidenceRecord } from "@/features/evidence/evidence-index";
import { useUiStore } from "@/stores/ui-store";

export function EvidenceItem({
  evidence,
  paper,
}: {
  evidence: EvidenceRecord;
  paper?: Record<string, unknown>;
}) {
  const t = useTranslations("evidence");
  const selectObject = useUiStore((state) => state.selectObject);
  const setContextTab = useUiStore((state) => state.setContextTab);
  const verified = evidence.verified !== false;
  const pageStart =
    typeof evidence.page_start === "number" ? evidence.page_start : null;
  const pageEnd =
    typeof evidence.page_end === "number" ? evidence.page_end : null;
  const paperId =
    typeof evidence.paper_id === "string" ? evidence.paper_id : "";
  return (
    <article className="space-y-3 rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface-subtle)] p-3">
      <div className="flex items-center justify-between gap-2">
        <Badge variant={verified ? "success" : "warning"}>
          {verified ? t("verified") : t("unverified")}
        </Badge>
        <span className="text-xs text-[var(--color-text-subtle)]">
          {String(evidence.content_type ?? "pdf")}
        </span>
      </div>
      <blockquote className="border-l-2 border-[var(--color-primary)] pl-3 text-sm leading-6 text-[var(--color-text)]">
        {String(evidence.excerpt ?? t("noExcerpt"))}
      </blockquote>
      <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-muted)]">
        {paper ? (
          <span>{String(paper.title ?? paperId)}</span>
        ) : (
          <span>{paperId || t("unknownPaper")}</span>
        )}
        {pageStart !== null ? (
          <span>
            {t("page", {
              page: `${pageStart}${pageEnd !== null && pageEnd !== pageStart ? `–${pageEnd}` : ""}`,
            })}
          </span>
        ) : null}
      </div>
      {!verified ? (
        <p className="flex items-start gap-1.5 text-xs text-[var(--color-warning)]">
          <AlertTriangle aria-hidden="true" className="mt-0.5 h-3.5 w-3.5" />
          {t("unverifiedExcerpt")}
        </p>
      ) : null}
      {paperId ? (
        <button
          type="button"
          className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-primary)]"
          onClick={() => {
            selectObject(paperId);
            setContextTab("papers");
          }}
        >
          <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
          {t("openPaper")}
        </button>
      ) : null}
    </article>
  );
}
