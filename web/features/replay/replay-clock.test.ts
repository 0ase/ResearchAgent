import { describe, expect, it } from "vitest";

import {
  compressEventGap,
  replayDelayMs,
} from "@/features/replay/replay-clock";
import type { ResearchEvent } from "@/lib/events/types";

const event = (occurred_at: string): ResearchEvent => ({
  schema_version: 1,
  task_id: "task-1",
  sequence: 1,
  event_type: "task.started",
  stage: null,
  level: "info",
  payload: {},
  occurred_at,
});

describe("replay clock", () => {
  it("keeps short gaps and compresses medium/long gaps", () => {
    expect(compressEventGap(2_000)).toBe(2_000);
    expect(compressEventGap(6_000)).toBe(1_500);
    expect(compressEventGap(20_000)).toBe(3_000);
  });

  it("applies playback speed after compression", () => {
    expect(
      replayDelayMs(
        event("2026-08-19T10:00:00Z"),
        event("2026-08-19T10:00:06Z"),
        2,
      ),
    ).toBe(750);
  });
});
