"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";

import { EvidenceItem } from "@/components/evidence/evidence-item";
import { InlineAlert } from "@/components/ui/inline-alert";
import { buildEvidenceIndex } from "@/features/evidence/evidence-index";
import type { ResearchTaskResultResponse } from "@/lib/api/client";
import { useUiStore } from "@/stores/ui-store";

export function EvidencePanel({
  result,
}: {
  result?: ResearchTaskResultResponse;
}) {
  const t = useTranslations("evidence");
  const selectedObjectId = useUiStore((state) => state.selectedObjectId);
  const index = useMemo(() => buildEvidenceIndex(result), [result]);
  const citation = selectedObjectId
    ? index.citations.get(selectedObjectId)
    : undefined;
  const evidence = selectedObjectId
    ? (index.evidenceByCitation.get(selectedObjectId) ?? [])
    : [];

  if (!result?.capabilities?.supports_evidence && !result?.evidence?.length) {
    return <p className="text-sm leading-6">{t("unsupported")}</p>;
  }
  if (!citation) {
    return <p className="text-sm leading-6">{t("empty")}</p>;
  }
  return (
    <section aria-label={t("details")} className="space-y-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
          {t("title")}
        </p>
        <h3 className="mt-1 text-sm font-semibold text-[var(--color-text)]">
          {t("citation", {
            number: String(citation.display_number ?? citation.citation_id),
          })}
        </h3>
        {citation.valid === false ? (
          <InlineAlert tone="warning" className="mt-2">
            {t("citationUnverified")}
          </InlineAlert>
        ) : null}
      </div>
      {evidence.length ? (
        evidence.map((item) => (
          <EvidenceItem
            key={String(item.evidence_id)}
            evidence={item}
            paper={index.papers.get(String(item.paper_id))}
          />
        ))
      ) : (
        <p className="text-sm">{t("noLinkedEvidence")}</p>
      )}
    </section>
  );
}
