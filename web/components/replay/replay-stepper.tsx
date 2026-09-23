"use client";

import type { ResearchStage, ReplayState } from "@/lib/events/types";
import { RESEARCH_STAGES } from "@/lib/events/types";
import { useTranslations } from "next-intl";
import {
  taskStageMessageKeys,
  taskStageStatusMessageKeys,
} from "@/i18n/task-labels";

export function ReplayStepper({
  state,
  onStage,
}: {
  state: ReplayState;
  onStage: (stage: ResearchStage) => void;
}) {
  const t = useTranslations();
  const taskT = useTranslations("task");
  return (
    <nav aria-label={t("replay.stageJump")} className="grid grid-cols-7 gap-1">
      {RESEARCH_STAGES.map((stage) => (
        <button
          key={stage}
          type="button"
          onClick={() => onStage(stage)}
          className="rounded-[var(--radius-control)] border border-[var(--color-border)] px-2 py-2 text-left text-xs hover:bg-[var(--color-surface-subtle)]"
        >
          <span
            className={
              state.currentStage === stage
                ? "font-semibold text-[var(--color-primary)]"
                : "text-[var(--color-text-muted)]"
            }
          >
            {taskT(taskStageMessageKeys[stage])}
          </span>
          <span className="mt-1 block text-[10px] text-[var(--color-text-subtle)]">
            {taskT(taskStageStatusMessageKeys[state.stages[stage].status])}
          </span>
        </button>
      ))}
    </nav>
  );
}
