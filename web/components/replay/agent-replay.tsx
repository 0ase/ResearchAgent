"use client";

import { InlineAlert } from "@/components/ui/inline-alert";
import { Skeleton } from "@/components/ui/skeleton";
import { EventInspector } from "@/components/replay/event-inspector";
import { EventTimeline } from "@/components/replay/event-timeline";
import { ReplayControls } from "@/components/replay/replay-controls";
import { ReplayStepper } from "@/components/replay/replay-stepper";
import { useTaskReplay } from "@/features/replay/hooks/use-task-replay";
import type { ResearchEvent } from "@/lib/events/types";
import { useTranslations } from "next-intl";

export function AgentReplay({
  taskId,
  events,
}: {
  taskId: string;
  events?: ResearchEvent[];
}) {
  const t = useTranslations("replay");
  const replay = useTaskReplay(taskId, { events });
  if (replay.isLoading)
    return (
      <div className="space-y-3 p-5">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  if (replay.error)
    return (
      <div className="p-5">
        <InlineAlert tone="error">{t("loadError")}</InlineAlert>
      </div>
    );
  if (!replay.supported)
    return (
      <div className="p-5">
        <InlineAlert tone="info">{t("unsupported")}</InlineAlert>
      </div>
    );
  return (
    <section aria-label={t("title")} className="space-y-5 p-5">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
            {t("persistedRun")}
          </p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--color-text)]">
            {t("title")}
          </h2>
          <p className="mt-1 text-xs text-[var(--color-text-muted)]">
            {replay.isFinished
              ? t("finished")
              : t("cursor", {
                  cursor: replay.eventCursor,
                  status: replay.state.taskStatus,
                })}
            {replay.state.critic.attempt > 1
              ? ` · ${t("criticRevision", { attempt: replay.state.critic.attempt })}`
              : ""}
          </p>
        </div>
        <ReplayControls
          isPlaying={replay.isPlaying}
          speed={replay.speed}
          onPlay={replay.play}
          onPause={replay.pause}
          onPrevious={replay.previous}
          onNext={replay.next}
          onSpeedChange={replay.setSpeed}
        />
      </header>
      <ReplayStepper state={replay.state} onStage={replay.jumpToStage} />
      <EventTimeline
        events={replay.events}
        cursor={replay.cursor}
        onSeek={replay.seek}
      />
      <EventInspector event={replay.events[replay.cursor - 1]} />
    </section>
  );
}
