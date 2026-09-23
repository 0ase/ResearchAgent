import type { ReplayState } from "@/lib/events/types";
import { taskStageMessageKeys } from "@/i18n/task-labels";
import { useTranslations } from "next-intl";

export function CurrentStagePanel({ state }: { state: ReplayState }) {
  const t = useTranslations("task");
  const stage = state.currentStage ? state.stages[state.currentStage] : null;
  return (
    <section className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-text-subtle)]">
        {t("stageDetail")}
      </p>
      <h2 className="mt-2 text-base font-semibold text-[var(--color-text)]">
        {state.currentStage
          ? t(taskStageMessageKeys[state.currentStage])
          : t("waitingToStart")}
      </h2>
      <p className="mt-1 text-sm text-[var(--color-text-muted)]">
        {stage?.detail ?? t("progressPlaceholder")}
      </p>
      {state.currentStage === "read" && state.metrics.read_total !== undefined ? (
        <p role="status" className="mt-2 text-sm text-[var(--color-text-muted)]">
          {t("readProgress", {
            total: state.metrics.read_total,
            completed: state.metrics.read_completed ?? 0,
            succeeded: state.metrics.read_succeeded ?? 0,
            degraded: state.metrics.read_degraded ?? 0,
            failed: state.metrics.read_failed ?? 0,
          })}
        </p>
      ) : null}
    </section>
  );
}
