import type { ResearchEvent } from "@/lib/events/types";
import { useTranslations } from "next-intl";

export function EventInspector({ event }: { event?: ResearchEvent }) {
  const t = useTranslations("replay");
  if (!event)
    return (
      <p className="text-sm text-[var(--color-text-muted)]">
        {t("inspectorEmpty")}
      </p>
    );
  return (
    <section
      aria-label={t("eventInspector")}
      className="space-y-3 rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-[var(--color-text)]">
          {event.event_type}
        </h3>
        <span className="text-xs text-[var(--color-text-subtle)]">
          {t("sequence", { sequence: event.sequence })}
        </span>
      </div>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-control)] bg-[var(--color-surface-subtle)] p-3 text-xs text-[var(--color-text-muted)]">
        {JSON.stringify(event.payload, null, 2)}
      </pre>
    </section>
  );
}
