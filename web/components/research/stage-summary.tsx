import type { ResearchStage, ReplayState } from "@/lib/events/types";
import { useTranslations } from "next-intl";
import {
  taskStageMessageKeys,
  taskStageStatusMessageKeys,
} from "@/i18n/task-labels";

export function StageSummary({
  state,
  stage,
}: {
  state: ReplayState;
  stage: ResearchStage;
}) {
  const t = useTranslations("task");
  const snapshot = state.stages[stage];
  return (
    <div className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface-subtle)] p-4">
      <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-text-subtle)]">
        {t("stageDetail")}
      </p>
      <p className="mt-1 text-sm text-[var(--color-text)]">
        {t(taskStageMessageKeys[stage])}
      </p>
      <p className="mt-1 text-xs text-[var(--color-text-muted)]">
        {t(taskStageStatusMessageKeys[snapshot.status])} ·{" "}
        {t("attempt", { attempt: snapshot.attempt })}
      </p>
    </div>
  );
}
