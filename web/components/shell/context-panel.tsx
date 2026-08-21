"use client";

import { FileText, Library, ListTree } from "lucide-react";
import { useTranslations } from "next-intl";

import { EvidencePanel } from "@/components/evidence/evidence-panel";
import { PaperDetail } from "@/components/papers/paper-detail";
import {
  normalizePaper,
  type ResearchPaper,
} from "@/features/papers/paper-model";
import { useTaskResult } from "@/features/tasks/hooks/use-task-result";
import { useTaskEvents } from "@/features/tasks/hooks/use-task-events";
import type { ResearchTaskResultResponse } from "@/lib/api/client";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUiStore, type ContextTab } from "@/stores/ui-store";
import { RESEARCH_STAGES } from "@/lib/events/types";
import {
  taskStageMessageKeys,
  taskStageStatusMessageKeys,
  taskStatusMessageKeys,
} from "@/i18n/task-labels";

export function ContextPanel({ taskId }: { taskId?: string }) {
  return taskId ? (
    <ContextPanelWithTask taskId={taskId} />
  ) : (
    <ContextPanelContent />
  );
}

function ContextPanelWithTask({ taskId }: { taskId: string }) {
  const resultQuery = useTaskResult(taskId, true);
  const events = useTaskEvents(taskId);
  const selectedObjectId = useUiStore((state) => state.selectedObjectId);
  const selectedPaper =
    resultQuery.data?.papers
      ?.map((paper, index) => normalizePaper(paper, index))
      .find((paper) => paper.id === selectedObjectId) ?? null;
  const citations = selectedPaper
    ? (resultQuery.data?.citations ?? [])
        .filter((citation) => citation.paper_id === selectedPaper.id)
        .map((citation) => ({
          citationId: citation.citation_id,
          displayNumber: citation.display_number,
        }))
    : [];
  return (
    <ContextPanelContent
      result={resultQuery.data}
      selectedPaper={selectedPaper}
      citations={citations}
      replayState={events.replayState}
      runError={events.error}
    />
  );
}

function ContextPanelContent({
  result,
  selectedPaper = null,
  replayState,
  runError,
  citations = [],
}: {
  result?: ResearchTaskResultResponse;
  selectedPaper?: ResearchPaper | null;
  replayState?: ReturnType<typeof useTaskEvents>["replayState"];
  runError?: Error | null;
  citations?: { citationId: string; displayNumber?: number | null }[];
}) {
  const t = useTranslations();
  const contextTab = useUiStore((state) => state.contextTab);
  const setContextTab = useUiStore((state) => state.setContextTab);

  return (
    <aside
      aria-label={t("common.contextPanel")}
      className="flex min-h-0 flex-col border-l border-[var(--color-border)] bg-[var(--color-surface)]"
    >
      <div className="flex h-14 items-center border-b border-[var(--color-border)] px-4">
        <h2 className="text-sm font-semibold text-[var(--color-text)]">
          {t("common.context")}
        </h2>
      </div>
      <Tabs
        value={contextTab}
        onValueChange={(value) => setContextTab(value as ContextTab)}
        className="flex min-h-0 flex-1 flex-col"
      >
        <TabsList aria-label={t("common.context")} className="mx-4 mt-2">
          <TabsTrigger value="evidence">
            <FileText aria-hidden="true" className="mr-1.5 h-3.5 w-3.5" />
            {t("common.evidence")}
          </TabsTrigger>
          <TabsTrigger value="papers">
            <Library aria-hidden="true" className="mr-1.5 h-3.5 w-3.5" />
            {t("common.papers")}
          </TabsTrigger>
          <TabsTrigger value="run">
            <ListTree aria-hidden="true" className="mr-1.5 h-3.5 w-3.5" />
            {t("common.runDetails")}
          </TabsTrigger>
        </TabsList>
        <div className="min-h-0 flex-1 overflow-y-auto p-4 text-sm text-[var(--color-text-muted)]">
          <TabsContent value="evidence" className="mt-0">
            <EvidencePanel result={result} />
          </TabsContent>
          <TabsContent value="papers" className="mt-0">
            <PaperDetail paper={selectedPaper} citations={citations} />
          </TabsContent>
          <TabsContent value="run" className="mt-0">
            <RunDetails replayState={replayState} error={runError} />
          </TabsContent>
        </div>
      </Tabs>
    </aside>
  );
}

function RunDetails({
  replayState,
  error,
}: {
  replayState?: ReturnType<typeof useTaskEvents>["replayState"];
  error?: Error | null;
}) {
  const t = useTranslations();
  const taskT = useTranslations("task");
  if (error) {
    return (
      <p className="text-sm text-[var(--color-error)]">{t("task.loadError")}</p>
    );
  }
  if (!replayState) {
    return (
      <p className="text-sm leading-6 text-[var(--color-text-muted)]">
        {t("task.noTaskContext")}
      </p>
    );
  }
  return (
    <div className="space-y-4">
      <div className="rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface-subtle)] p-3">
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[var(--color-text-subtle)]">
          {t("task.runDetails")}
        </p>
        <p className="mt-1 text-sm font-medium text-[var(--color-text)]">
          {replayState.currentStage
            ? taskT(taskStageMessageKeys[replayState.currentStage])
            : t("common.notAvailable")}
        </p>
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">
          {taskT(taskStatusMessageKeys[replayState.taskStatus])}
        </p>
      </div>
      <div className="space-y-2">
        {RESEARCH_STAGES.map((stage) => {
          const snapshot = replayState.stages[stage];
          return (
            <div
              key={stage}
              className="flex items-center justify-between gap-3 text-xs"
            >
              <span className="text-[var(--color-text-muted)]">
                {taskT(taskStageMessageKeys[stage])}
              </span>
              <span className="text-[var(--color-text-subtle)]">
                {snapshot.durationMs == null
                  ? taskT(taskStageStatusMessageKeys[snapshot.status])
                  : `${snapshot.durationMs} ms`}
              </span>
            </div>
          );
        })}
      </div>
      {replayState.warnings.length || replayState.errors.length ? (
        <div className="border-t border-[var(--color-border)] pt-3 text-xs text-[var(--color-text-muted)]">
          {[...replayState.warnings, ...replayState.errors]
            .slice(-3)
            .map((message) => (
              <p key={message} className="mt-1">
                {message}
              </p>
            ))}
        </div>
      ) : null}
    </div>
  );
}
