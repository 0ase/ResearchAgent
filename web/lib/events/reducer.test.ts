import { describe, expect, it } from "vitest";

import {
  allEventTypes,
  eventSchemas,
  parseResearchEvent,
  researchEventSchema,
} from "@/lib/events/schemas";
import {
  createInitialReplayState,
  reduceResearchEvent,
  replayEvents,
} from "@/lib/events/reducer";
import {
  criticRevisionEvents,
  failureEvents,
  partialSuccessEvents,
  successEvents,
} from "@/lib/events/fixtures";
import type { EventType } from "@/lib/events/types";

const taskId = "task-reducer-1";

function event(
  eventType: EventType | string,
  sequence: number,
  payload: Record<string, unknown> = {},
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    schema_version: 1,
    task_id: taskId,
    sequence,
    event_type: eventType,
    level: "info",
    payload,
    occurred_at: `2026-08-19T10:00:${String(sequence).padStart(2, "0")}Z`,
    ...overrides,
  };
}

describe("research event schemas", () => {
  it("accepts every standard event type through its discriminated schema", () => {
    for (const eventType of allEventTypes) {
      const result = eventSchemas[eventType].safeParse(event(eventType, 1));
      expect(result.success, eventType).toBe(true);
      expect(researchEventSchema.safeParse(event(eventType, 1)).success).toBe(
        true,
      );
    }
  });

  it.each(["task_id", "sequence", "schema_version"])(
    "rejects an event without %s",
    (field) => {
      const candidate = event("task.created", 1);
      delete candidate[field];

      expect(parseResearchEvent(candidate).status).toBe("rejected");
    },
  );
});

describe("research event replay reducer", () => {
  it("ignores unknown events instead of throwing into the page boundary", () => {
    const result = reduceResearchEvent(
      createInitialReplayState(taskId),
      event("future.event", 1),
    );

    expect(result).toMatchObject({
      status: "ignored",
      reason: "unknown_event",
    });
    expect(result.state.lastSequence).toBe(0);
  });

  it("does not count a duplicate sequence twice", () => {
    const initial = createInitialReplayState(taskId);
    const first = reduceResearchEvent(
      initial,
      event("papers.discovered", 1, { count: 4 }),
    );
    const duplicate = reduceResearchEvent(
      first.state,
      event("papers.discovered", 1, { count: 99 }),
    );

    expect(first.state.metrics.papersDiscovered).toBe(4);
    expect(duplicate).toMatchObject({
      status: "ignored",
      reason: "duplicate_sequence",
    });
    expect(duplicate.state.metrics.papersDiscovered).toBe(4);
  });

  it("rejects out-of-order events without moving the cursor backwards", () => {
    const first = reduceResearchEvent(
      createInitialReplayState(taskId),
      event("task.started", 2),
    );
    const outOfOrder = reduceResearchEvent(
      first.state,
      event("task.created", 1),
    );

    expect(outOfOrder).toMatchObject({
      status: "ignored",
      reason: "out_of_order",
    });
    expect(outOfOrder.state.lastSequence).toBe(2);
    expect(outOfOrder.state.taskStatus).toBe("running");
  });

  it("rebuilds stage snapshots from started, progress, and completed events", () => {
    const state = replayEvents(taskId, [
      event("stage.started", 1, { attempt: 1 }, { stage: "search" }),
      event(
        "stage.progress",
        2,
        { message: "Searching sources", metrics: { hits: 12 } },
        { stage: "search" },
      ),
      event(
        "stage.completed",
        3,
        { duration_ms: 420, detail: "12 papers" },
        { stage: "search" },
      ),
    ]);

    expect(state.stages.search).toMatchObject({
      status: "completed",
      detail: "12 papers",
      durationMs: 420,
      startedAt: "2026-08-19T10:00:01Z",
      completedAt: "2026-08-19T10:00:03Z",
    });
    expect(state.metrics.hits).toBe(12);
  });

  it("keeps the critic revision attempt across the revision cycle", () => {
    const state = replayEvents(taskId, [
      event("stage.started", 1, { attempt: 1 }, { stage: "critic" }),
      event(
        "critique.completed",
        2,
        { attempt: 1, summary: "Revise citations" },
        { stage: "critic" },
      ),
      event("stage.started", 3, { attempt: 2 }, { stage: "critic" }),
      event(
        "critique.completed",
        4,
        { attempt: 2, summary: "Ready" },
        { stage: "critic" },
      ),
    ]);

    expect(state.critic).toMatchObject({ attempt: 2, summary: "Ready" });
    expect(state.stages.critic.attempt).toBe(2);
  });

  it.each([
    ["task.completed", "completed"],
    ["task.failed", "failed"],
    ["task.cancelled", "cancelled"],
  ] as const)("moves %s into a terminal state", (eventType, status) => {
    const state = replayEvents(taskId, [event(eventType, 1)]);

    expect(state.taskStatus).toBe(status);
    expect(state.isTerminal).toBe(true);
  });

  it("uses the same pure reducer for realtime and replay", () => {
    const fixtureTaskId = successEvents[0].task_id;
    const realtime = successEvents.reduce(
      (state, current) => reduceResearchEvent(state, current).state,
      createInitialReplayState(fixtureTaskId),
    );
    const replayed = replayEvents(fixtureTaskId, successEvents);

    expect(replayed).toEqual(realtime);
    expect(replayed.lastSequence).toBe(successEvents.length);
    expect(partialSuccessEvents.length).toBeGreaterThan(0);
    expect(criticRevisionEvents.length).toBeGreaterThan(0);
    expect(failureEvents.length).toBeGreaterThan(0);
  });

  it("rejects an event from another task without changing state", () => {
    const result = reduceResearchEvent(
      createInitialReplayState(taskId),
      event("task.created", 1, {}, { task_id: "another-task" }),
    );

    expect(result).toMatchObject({
      status: "rejected",
      reason: "task_mismatch",
    });
    expect(result.state.lastSequence).toBe(0);
  });
});

describe("event fixtures", () => {
  it("keeps fixtures valid against the public schema", () => {
    for (const fixture of [
      ...successEvents,
      ...partialSuccessEvents,
      ...criticRevisionEvents,
      ...failureEvents,
    ]) {
      expect(researchEventSchema.safeParse(fixture).success).toBe(true);
    }
  });
});
