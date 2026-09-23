import { describe, expect, it } from "vitest";

import {
  replayStateToSnapshot,
  snapshotToReplayState,
} from "@/features/tasks/task-cache";
import { taskSnapshotSchema } from "@/lib/api/response-schemas";
import { reduceResearchEvent } from "@/lib/events/reducer";

const snapshot = {
  id: "task",
  client_request_id: "request",
  query: "Question",
  title: "Title",
  status: "running",
  effective_locale: "en",
  last_sequence: 0,
  created_at: "2026-09-07T00:00:00Z",
  replay_events: [],
};
const event = {
  task_id: "task",
  schema_version: 1,
  sequence: 1,
  event_type: "draft.available",
  stage: "synthesize",
  level: "info",
  payload: { count: 1 },
  occurred_at: snapshot.created_at,
};

describe("durable snapshot replay", () => {
  it("preserves applied artifacts in cache for a page remount", () => {
    const initial = taskSnapshotSchema.parse(snapshot);
    const applied = reduceResearchEvent(snapshotToReplayState(initial), event);
    expect(applied.status).toBe("applied");
    if (applied.status !== "applied")
      throw new Error("Expected an applied event");
    const cached = replayStateToSnapshot(initial, applied.state, applied.event);
    expect(snapshotToReplayState(cached)).toEqual(applied.state);
    expect(
      replayStateToSnapshot(cached, applied.state, applied.event).replay_events,
    ).toHaveLength(1);
  });

  it("tolerates future event types but rejects malformed known events", () => {
    expect(
      taskSnapshotSchema.safeParse({
        ...snapshot,
        replay_events: [{ ...event, event_type: "future.event" }],
      }).success,
    ).toBe(true);
    expect(
      taskSnapshotSchema.safeParse({
        ...snapshot,
        replay_events: [
          { ...event, event_type: "agent.delegated", payload: {} },
        ],
      }).success,
    ).toBe(false);
  });
});
