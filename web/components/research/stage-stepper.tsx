"use client";

import {
  Check,
  Circle,
  CircleAlert,
  CircleX,
  LoaderCircle,
  Pause,
} from "lucide-react";
import { useTranslations } from "next-intl";

import type {
  ResearchStage,
  ReplayState,
  StageStatus,
} from "@/lib/events/types";
import { RESEARCH_STAGES } from "@/lib/events/types";
import {
  taskStageMessageKeys,
  taskStageStatusMessageKeys,
} from "@/i18n/task-labels";

export function StageStepper({
  state,
  onSelectStage,
}: {
  state: ReplayState;
  onSelectStage?: (stage: ResearchStage) => void;
}) {
  const t = useTranslations("task");
  const stages = RESEARCH_STAGES;
  return (
    <nav
      aria-label={t("stageDetail")}
      className="flex items-start gap-1 overflow-x-auto pb-2"
    >
      {stages.map((stage) => {
        const snapshot = state.stages[stage];
        return (
          <button
            key={stage}
            type="button"
            aria-label={
              t(taskStageMessageKeys[stage]) +
              " " +
              t(taskStageStatusMessageKeys[snapshot.status])
            }
            data-status={snapshot.status}
            onClick={() => onSelectStage?.(stage)}
            className="group flex min-w-20 flex-1 flex-col items-center gap-1 rounded-[var(--radius-control)] px-1 py-1 text-center outline-none transition-colors hover:bg-[var(--color-surface-subtle)] focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-text-subtle)] group-data-[status=running]:border-[var(--color-primary)] group-data-[status=running]:text-[var(--color-primary)]">
              <StageIcon status={snapshot.status} />
            </span>
            <span className="text-xs font-medium text-[var(--color-text-muted)]">
              {t(taskStageMessageKeys[stage])}
            </span>
            {stage === "critic" && snapshot.attempt > 1 ? (
              <span className="text-[10px] text-[var(--color-text-subtle)]">
                {t("attempt", { attempt: snapshot.attempt })}
              </span>
            ) : null}
          </button>
        );
      })}
    </nav>
  );
}

function StageIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case "running":
      return (
        <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
      );
    case "completed":
      return (
        <Check
          aria-hidden="true"
          className="h-4 w-4 text-[var(--color-success)]"
        />
      );
    case "warning":
      return (
        <CircleAlert
          aria-hidden="true"
          className="h-4 w-4 text-[var(--color-warning)]"
        />
      );
    case "failed":
      return (
        <CircleX
          aria-hidden="true"
          className="h-4 w-4 text-[var(--color-error)]"
        />
      );
    case "cancelled":
      return (
        <Pause
          aria-hidden="true"
          className="h-4 w-4 text-[var(--color-text-muted)]"
        />
      );
    default:
      return <Circle aria-hidden="true" className="h-4 w-4" />;
  }
}
