"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { PaperDetail } from "@/components/papers/paper-detail";
import { PaperList } from "@/components/papers/paper-list";
import { ExportMenu } from "@/components/report/export-menu";
import { ReportDocument } from "@/components/report/report-document";
import { ReportSummary } from "@/components/report/report-summary";
import { ReportToc } from "@/components/report/report-toc";
import { QualityReview } from "@/components/report/quality-review";
import { AgentReplay } from "@/components/replay/agent-replay";
import { InlineAlert } from "@/components/ui/inline-alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useTaskResult } from "@/features/tasks/hooks/use-task-result";
import {
  normalizePaper,
  type ResearchPaper,
} from "@/features/papers/paper-model";
import type { ResearchTaskResultResponse } from "@/lib/api/client";
import { useUiStore } from "@/stores/ui-store";

const statisticLabels = {
  papers_count: "report.statistics.papersCount",
  selected_papers_count: "report.statistics.selectedPapersCount",
  paper_insights_count: "report.statistics.paperInsightsCount",
  papers_read: "report.statistics.papersRead",
  critique_score: "report.statistics.critiqueScore",
  critique_round: "report.statistics.critiqueRound",
  paper_claims_count: "report.statistics.paperClaimsCount",
  analysis_findings_count: "report.statistics.analysisFindingsCount",
  duration_ms: "report.statistics.durationMs",
} as const;

export function ReportView({
  taskId,
  result: providedResult,
}: {
  taskId: string;
  result?: ResearchTaskResultResponse;
}) {
  const query = useTaskResult(taskId, !providedResult);
  const result = providedResult ?? query.data;
  const papers = useMemo(
    () =>
      (result?.papers ?? []).map((paper, index) =>
        normalizePaper(paper, index),
      ),
    [result?.papers],
  );
  const [selectedPaper, setSelectedPaper] = useState<ResearchPaper | null>(
    null,
  );
  const selectObject = useUiStore((state) => state.selectObject);
  const setContextTab = useUiStore((state) => state.setContextTab);
  const t = useTranslations();
  const handleSelectPaper = (paper: ResearchPaper) => {
    setSelectedPaper(paper);
    selectObject(paper.id);
    setContextTab("papers");
  };

  if (!result) {
    if (query.isError)
      return (
        <div className="p-8">
          <InlineAlert tone="error">{t("report.noReport")}</InlineAlert>
        </div>
      );
    return (
      <div className="space-y-4 p-8">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <article className="mx-auto w-full max-w-5xl px-8 py-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
            {t("report.title")}
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-[var(--color-text)]">
            {t("report.synthesis")}
          </h1>
          <div className="mt-2">
            <ReportSummary result={result} />
          </div>
        </div>
        <ExportMenu taskId={taskId} />
      </header>
      <Tabs defaultValue="report" className="mt-6">
        <TabsList aria-label={t("report.views")}>
          <TabsTrigger value="report">{t("report.reportTab")}</TabsTrigger>
          <TabsTrigger value="papers">
            {t("report.papersTab", { count: papers.length })}
          </TabsTrigger>
          <TabsTrigger value="run">{t("report.runTab")}</TabsTrigger>
        </TabsList>
        <TabsContent value="report" className="pt-5">
          <div className="grid gap-6 lg:grid-cols-[200px_minmax(0,760px)]">
            <ReportToc markdown={result.report_markdown} />
            <div className="space-y-6">
              <QualityReview result={result} />
              <ReportDocument
                markdown={result.report_markdown}
                result={result}
              />
            </div>
          </div>
        </TabsContent>
        <TabsContent value="papers" className="pt-5">
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
            <PaperList
              papers={papers}
              selectedPaperId={selectedPaper?.id}
              onSelect={handleSelectPaper}
            />
            <PaperDetail
              paper={selectedPaper}
              citations={(result.citations ?? [])
                .filter((citation) => citation.paper_id === selectedPaper?.id)
                .map((citation) => ({
                  citationId: citation.citation_id,
                  displayNumber: citation.display_number,
                }))}
            />
          </div>
        </TabsContent>
        <TabsContent value="run" className="pt-5">
          <section className="space-y-4 rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <h2 className="text-base font-semibold text-[var(--color-text)]">
              {t("report.runTab")}
            </h2>
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              {Object.entries(result.statistics ?? {}).map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-[var(--radius-control)] bg-[var(--color-surface-subtle)] px-3 py-2"
                >
                  <dt className="text-xs text-[var(--color-text-subtle)]">
                    {key in statisticLabels
                      ? t(statisticLabels[key as keyof typeof statisticLabels])
                      : key}
                  </dt>
                  <dd className="mt-1 text-[var(--color-text)]">
                    {typeof value === "string" || typeof value === "number"
                      ? String(value)
                      : t("common.notAvailable")}
                  </dd>
                </div>
              ))}
            </dl>
            <details className="rounded-[var(--radius-control)] border border-[var(--color-border)]">
              <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-[var(--color-text)]">
                {t("report.runReplay")}
              </summary>
              <AgentReplay taskId={taskId} />
            </details>
          </section>
        </TabsContent>
      </Tabs>
    </article>
  );
}
