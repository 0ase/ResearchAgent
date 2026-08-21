"use client";

import { useUiStore } from "@/stores/ui-store";
import { useTranslations } from "next-intl";

export function CitationMarker({
  citationId,
  displayNumber,
  valid = true,
}: {
  citationId: string;
  displayNumber?: number;
  valid?: boolean;
}) {
  const t = useTranslations("report");
  const selectObject = useUiStore((state) => state.selectObject);
  const setContextTab = useUiStore((state) => state.setContextTab);
  const open = () => {
    selectObject(citationId);
    setContextTab("evidence");
  };
  return (
    <button
      type="button"
      className={
        valid ? "citation-marker" : "citation-marker citation-marker-invalid"
      }
      aria-label={t("openCitation", { number: displayNumber ?? citationId })}
      title={valid ? t("openEvidence") : t("unverifiedCitation")}
      onClick={open}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") open();
      }}
    >
      {displayNumber ?? t("citationFallback", { id: citationId })}
    </button>
  );
}
