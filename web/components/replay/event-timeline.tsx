"use client";

import type { ResearchEvent } from "@/lib/events/types";
import { useTranslations } from "next-intl";

export function EventTimeline({
  events,
  cursor,
  onSeek,
}: {
  events: readonly ResearchEvent[];
  cursor: number;
  onSeek: (cursor: number) => void;
}) {
  const t = useTranslations("replay");
  return (
    <section aria-label={t("eventTimeline")} className="space-y-2">
      <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
        <span>
          {t("eventCount", { current: cursor, total: events.length })}
        </span>
        <span>{events[cursor - 1]?.event_type ?? t("ready")}</span>
      </div>
      <input
        aria-label={t("seek")}
        type="range"
        min={0}
        max={events.length}
        value={cursor}
        onChange={(event) => onSeek(Number(event.target.value))}
        className="w-full accent-[var(--color-primary)]"
      />
      <div className="flex gap-1 overflow-x-auto pb-1">
        {events.map((event, index) => (
          <button
            key={event.sequence}
            type="button"
            aria-label={t("goToEvent", { sequence: event.sequence })}
            onClick={() => onSeek(index + 1)}
            className={
              index < cursor
                ? "h-1.5 min-w-5 rounded-full bg-[var(--color-primary)]"
                : "h-1.5 min-w-5 rounded-full bg-[var(--color-border-strong)]"
            }
          />
        ))}
      </div>
    </section>
  );
}
