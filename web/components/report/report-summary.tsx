import { FileWarning } from "lucide-react";
import { useTranslations } from "next-intl";

import type { ResearchTaskResultResponse } from "@/lib/api/client";

export function ReportSummary({
  result,
}: {
  result: ResearchTaskResultResponse;
}) {
  const t = useTranslations("report");
  const papersRead =
    typeof result.statistics?.papers_read === "number"
      ? result.statistics.papers_read
      : (result.papers?.length ?? 0);
  const criticAttempt =
    typeof result.critique?.attempt === "number"
      ? result.critique.attempt
      : null;

  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--color-text-muted)]">
      <span>{t("papersRead", { count: papersRead })}</span>
      {result.partial ? (
        <span className="inline-flex items-center gap-1 text-[var(--color-warning)]">
          <FileWarning aria-hidden="true" className="h-3.5 w-3.5" />{" "}
          {t("partialResult")}
        </span>
      ) : null}
      {criticAttempt ? (
        <span>{t("criticAttempt", { attempt: criticAttempt })}</span>
      ) : null}
    </div>
  );
}
