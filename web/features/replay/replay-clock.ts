import type { ResearchEvent } from "@/lib/events/types";

export function compressEventGap(gapMs: number): number {
  const gap = Math.max(0, gapMs);
  if (gap <= 2_000) return gap;
  if (gap <= 10_000) return 1_000 + ((gap - 2_000) / 8_000) * 1_000;
  return Math.min(3_000, 2_000 + ((gap - 10_000) / 10_000) * 1_000);
}

export function replayDelayMs(
  previous: ResearchEvent | undefined,
  current: ResearchEvent | undefined,
  speed: 1 | 2 | 4 = 1,
): number {
  if (!current) return 0;
  if (!previous) return 250 / speed;
  const previousTime = Date.parse(previous.occurred_at);
  const currentTime = Date.parse(current.occurred_at);
  const gap =
    Number.isFinite(previousTime) && Number.isFinite(currentTime)
      ? currentTime - previousTime
      : 1_000;
  return compressEventGap(gap) / speed;
}

export function delayForCursor(
  events: readonly ResearchEvent[],
  cursor: number,
  speed: 1 | 2 | 4 = 1,
): number {
  return replayDelayMs(events[cursor - 1], events[cursor], speed);
}
